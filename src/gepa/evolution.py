"""
GEPA Evolution Engine - Genetic-Pareto prompt optimization.

Implements the GEPA cycle:
1. Sample agent trajectories (reasoning paths, tool calls, outputs)
2. Reflect on failures in natural language to diagnose problems
3. Propose prompt revisions based on reflection
4. Test variants and maintain Pareto frontier
5. Combine complementary lessons iteratively
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml


def _expand_env_vars(config: Any) -> Any:
    """Recursively expand ${VAR} and ${VAR:-default} patterns in config values."""
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        def replace(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)
        return re.sub(pattern, replace, config)
    return config


@dataclass
class Trajectory:
    """A single agent execution trajectory."""
    task: str
    prompt: str
    output: str
    expected: Optional[str] = None
    error: Optional[str] = None
    success: bool = True
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "prompt": self.prompt,
            "output": self.output,
            "expected": self.expected,
            "error": self.error,
            "success": self.success,
            "tool_calls": self.tool_calls,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Reflection:
    """Natural language reflection on a failed trajectory."""
    failure: Trajectory
    diagnosis: str
    root_cause: str = ""
    missing_context: str = ""
    suggested_improvement: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.failure.task,
            "error": self.failure.error,
            "diagnosis": self.diagnosis,
            "root_cause": self.root_cause,
            "missing_context": self.missing_context,
            "suggested_improvement": self.suggested_improvement,
        }


@dataclass
class PromptVariant:
    """A variant of a system prompt with its scores."""
    id: str
    model: str
    content: str
    parent_id: Optional[str] = None
    generation: int = 0
    scores: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def dominates(self, other: "PromptVariant") -> bool:
        """Check if this variant Pareto-dominates another."""
        if not self.scores or not other.scores:
            return False

        common_objectives = set(self.scores.keys()) & set(other.scores.keys())
        if not common_objectives:
            return False

        at_least_one_better = False
        for obj in common_objectives:
            if self.scores[obj] < other.scores[obj]:
                return False
            if self.scores[obj] > other.scores[obj]:
                at_least_one_better = True

        return at_least_one_better

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "content": self.content,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "scores": self.scores,
            "created_at": self.created_at.isoformat(),
        }


class GEPAEvolutionEngine:
    """
    Genetic-Pareto prompt optimization via natural language reflection.
    """

    def __init__(
        self,
        oracle_endpoint: str = "http://deepseek-v32:8000/v1",
        eval_endpoint: str = "http://braintrust:8020",
        config_path: str = "/nvme/gepa/config.yaml",
        state_path: str = "/nvme/gepa/state",
    ):
        self.oracle_endpoint = oracle_endpoint
        self.eval_endpoint = eval_endpoint
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.logger = logging.getLogger(__name__)

        self.pareto_frontier: List[PromptVariant] = []
        self.trajectory_buffer: List[Trajectory] = []
        self.config: Dict[str, Any] = {}

        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(timeout=120.0)
        await self._load_config()
        await self._load_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._save_state()
        if self._http_client:
            await self._http_client.aclose()

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def _load_config(self):
        """Load GEPA configuration from YAML with env var expansion."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                raw_config = yaml.safe_load(f)
                self.config = _expand_env_vars(raw_config)
        else:
            self.config = {
                "trajectory_sample_size": 100,
                "pareto_frontier_size": 10,
                "golden_dataset": "/nvme/eval/golden/",
                "targets": [],
            }

    async def _load_state(self):
        """Load persisted Pareto frontier and trajectory buffer."""
        state_file = self.state_path / "pareto_frontier.json"
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
                for v in data.get("frontier", []):
                    try:
                        if "created_at" in v and isinstance(v["created_at"], str):
                            v["created_at"] = datetime.fromisoformat(v["created_at"])
                    except ValueError:
                        self.logger.warning("Invalid created_at in variant, using now()")
                        v["created_at"] = datetime.now()
                    try:
                        self.pareto_frontier.append(PromptVariant(**v))
                    except Exception as e:
                        self.logger.warning(f"Skipping malformed variant: {e}")

    async def _save_state(self):
        """Persist Pareto frontier to disk."""
        self.state_path.mkdir(parents=True, exist_ok=True)
        state_file = self.state_path / "pareto_frontier.json"
        with open(state_file, "w") as f:
            json.dump({
                "frontier": [v.to_dict() for v in self.pareto_frontier],
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2)

    def record_trajectory(self, trajectory: Trajectory):
        """Record a trajectory for later analysis."""
        self.trajectory_buffer.append(trajectory)
        max_buffer = self.config.get("trajectory_sample_size", 100) * 2
        if len(self.trajectory_buffer) > max_buffer:
            self.trajectory_buffer = self.trajectory_buffer[-max_buffer:]

    async def evolution_cycle(self, current_prompts: Dict[str, str]) -> Dict[str, str]:
        """
        Run a full GEPA evolution cycle.

        Args:
            current_prompts: Dict mapping model names to current system prompts

        Returns:
            Dict mapping model names to improved system prompts
        """
        self.logger.info("Starting GEPA evolution cycle")

        sample_size = self.config.get("trajectory_sample_size", 100)
        trajectories = self.trajectory_buffer[-sample_size:]
        self.logger.info(f"Step 1: Sampled {len(trajectories)} trajectories")

        failures = [t for t in trajectories if not t.success]
        self.logger.info(f"Step 2: Found {len(failures)} failures to analyze")

        if not failures:
            self.logger.info("No failures to reflect on, skipping cycle")
            return current_prompts

        reflections = await self._reflect_on_failures(failures[:20])
        self.logger.info(f"Step 2: Generated {len(reflections)} reflections")

        variants = await self._propose_variants(current_prompts, reflections)
        self.logger.info(f"Step 3: Proposed {len(variants)} prompt variants")

        scores = await self._benchmark_variants(variants)
        self.logger.info("Step 4: Benchmarked variants")

        for variant in variants:
            if variant.id in scores:
                variant.scores = scores[variant.id]

        self._update_pareto_frontier(variants)
        self.logger.info(f"Step 5: Pareto frontier has {len(self.pareto_frontier)} variants")

        improved_prompts = self._combine_lessons()
        self.logger.info("Step 6: Combined lessons into improved prompts")

        await self._save_state()

        return improved_prompts

    async def _reflect_on_failures(self, failures: List[Trajectory]) -> List[Reflection]:
        """Use the Oracle to analyze why failures occurred."""
        reflections = []

        for failure in failures:
            prompt = f"""Analyze this agent failure:

Task: {failure.task}
Agent Output: {failure.output[:1000]}
Expected: {failure.expected or 'Not specified'}
Error: {failure.error or 'Task marked as failed'}

Diagnose the root cause in natural language. Respond with JSON:
{{
    "diagnosis": "Overall analysis of what went wrong",
    "root_cause": "The fundamental reason for the failure",
    "missing_context": "What information was missing that led to the error",
    "suggested_improvement": "How the system prompt could be improved"
}}"""

            try:
                response = await self._call_oracle(prompt)
                data = json.loads(response)

                reflections.append(Reflection(
                    failure=failure,
                    diagnosis=data.get("diagnosis", ""),
                    root_cause=data.get("root_cause", ""),
                    missing_context=data.get("missing_context", ""),
                    suggested_improvement=data.get("suggested_improvement", ""),
                ))
            except Exception as e:
                self.logger.error(f"Failed to reflect on failure: {e}")

        return reflections

    async def _propose_variants(
        self,
        current_prompts: Dict[str, str],
        reflections: List[Reflection],
    ) -> List[PromptVariant]:
        """Generate prompt variants based on reflections."""
        variants = []

        reflection_summary = "\n\n".join([
            f"Issue: {r.root_cause}\nSuggestion: {r.suggested_improvement}"
            for r in reflections[:10]
        ])

        for model, current_prompt in current_prompts.items():
            propose_prompt = f"""Given this current system prompt and the issues found:

CURRENT PROMPT:
{current_prompt[:2000]}

ISSUES AND SUGGESTIONS:
{reflection_summary}

Generate 3 improved versions of this system prompt that address the issues.
Respond with JSON:
{{
    "variants": [
        {{"content": "improved prompt 1", "changes": "what was changed"}},
        {{"content": "improved prompt 2", "changes": "what was changed"}},
        {{"content": "improved prompt 3", "changes": "what was changed"}}
    ]
}}"""

            try:
                response = await self._call_oracle(propose_prompt)
                data = json.loads(response)

                for i, v in enumerate(data.get("variants", [])):
                    variant_id = f"{model}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
                    variants.append(PromptVariant(
                        id=variant_id,
                        model=model,
                        content=v.get("content", current_prompt),
                        parent_id=f"{model}_current",
                        generation=len(self.pareto_frontier) + 1,
                    ))
            except Exception as e:
                self.logger.error(f"Failed to propose variants for {model}: {e}")

        return variants

    async def _benchmark_variants(
        self,
        variants: List[PromptVariant]
    ) -> Dict[str, Dict[str, float]]:
        """Benchmark variants on the golden dataset concurrently."""

        async def benchmark_single(variant: PromptVariant) -> tuple[str, Dict[str, float]]:
            try:
                response = await self.http_client.post(
                    f"{self.eval_endpoint}/benchmark",
                    json={
                        "variant_id": variant.id,
                        "prompt": variant.content,
                        "model": variant.model,
                        "dataset": self.config.get("golden_dataset", "/nvme/eval/golden/"),
                    },
                    timeout=300.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return variant.id, data.get("scores", {
                        "accuracy": 0.5,
                        "latency": 1.0,
                        "tool_use_success": 0.5,
                    })
            except Exception as e:
                self.logger.error(f"Benchmark failed for {variant.id}: {e}")
            return variant.id, {"accuracy": 0.5}

        results = await asyncio.gather(
            *[benchmark_single(v) for v in variants],
            return_exceptions=True
        )

        scores = {}
        for result in results:
            if isinstance(result, tuple):
                variant_id, variant_scores = result
                scores[variant_id] = variant_scores
            elif isinstance(result, Exception):
                self.logger.error(f"Benchmark exception: {result}")

        return scores

    def _update_pareto_frontier(self, new_variants: List[PromptVariant]):
        """Update the Pareto frontier with non-dominated variants."""
        all_variants = self.pareto_frontier + new_variants

        non_dominated = []
        for candidate in all_variants:
            is_dominated = False
            for other in all_variants:
                if other.id != candidate.id and other.dominates(candidate):
                    is_dominated = True
                    break
            if not is_dominated:
                non_dominated.append(candidate)

        max_size = self.config.get("pareto_frontier_size", 10)
        if len(non_dominated) > max_size:
            non_dominated.sort(
                key=lambda v: sum(v.scores.values()) if v.scores else 0,
                reverse=True,
            )
            non_dominated = non_dominated[:max_size]

        self.pareto_frontier = non_dominated

    def _combine_lessons(self) -> Dict[str, str]:
        """Combine lessons from Pareto frontier into best prompts."""
        best_prompts = {}

        by_model: Dict[str, List[PromptVariant]] = {}
        for variant in self.pareto_frontier:
            if variant.model not in by_model:
                by_model[variant.model] = []
            by_model[variant.model].append(variant)

        for model, variants in by_model.items():
            if variants:
                best = max(
                    variants,
                    key=lambda v: v.scores.get("accuracy", 0) if v.scores else 0,
                )
                best_prompts[model] = best.content

        return best_prompts

    async def _call_oracle(self, prompt: str) -> str:
        """Call the Oracle for reflection and proposal tasks."""
        try:
            response = await self.http_client.post(
                f"{self.oracle_endpoint}/chat/completions",
                json={
                    "model": "deepseek-v32",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Oracle call failed: {e}")
        return "{}"

    async def get_pareto_frontier(self) -> List[Dict[str, Any]]:
        """Return current Pareto frontier as dict list."""
        return [v.to_dict() for v in self.pareto_frontier]


async def create_gepa_server(host: str = "0.0.0.0", port: int = 8010):
    """Create and run the GEPA HTTP server."""
    from contextlib import asynccontextmanager

    import uvicorn
    from fastapi import FastAPI
    from pydantic import BaseModel

    engine = GEPAEvolutionEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine._http_client = httpx.AsyncClient(timeout=120.0)
        await engine._load_config()
        await engine._load_state()
        yield
        await engine._save_state()
        if engine._http_client:
            await engine._http_client.aclose()

    app = FastAPI(title="GEPA Evolution Engine", version="14.0.0", lifespan=lifespan)

    class TrajectoryRequest(BaseModel):
        task: str
        prompt: str
        output: str
        expected: Optional[str] = None
        error: Optional[str] = None
        success: bool = True
        tool_calls: List[Dict[str, Any]] = []
        latency_ms: float = 0.0

    class EvolutionRequest(BaseModel):
        current_prompts: Dict[str, str]

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "14.0.0"}

    @app.get("/pareto-frontier")
    async def pareto_frontier():
        return {"frontier": await engine.get_pareto_frontier()}

    @app.post("/record-trajectory")
    async def record_trajectory(request: TrajectoryRequest):
        trajectory = Trajectory(
            task=request.task,
            prompt=request.prompt,
            output=request.output,
            expected=request.expected,
            error=request.error,
            success=request.success,
            tool_calls=request.tool_calls,
            latency_ms=request.latency_ms,
        )
        engine.record_trajectory(trajectory)
        return {"status": "recorded", "buffer_size": len(engine.trajectory_buffer)}

    @app.post("/evolve")
    async def evolve(request: EvolutionRequest):
        improved = await engine.evolution_cycle(request.current_prompts)
        await engine._save_state()
        return {"improved_prompts": improved}

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(create_gepa_server())
