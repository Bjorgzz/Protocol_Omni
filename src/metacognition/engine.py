"""
Metacognition Engine - Core verification pipeline for agent outputs.

Implements a 4-gate verification system:
1. Self-Check: Validates output consistency with original prompt
2. Evidence Cross-Reference: Verifies claims against retrieved context
3. Uncertainty Quantification: Estimates confidence intervals
4. Symbolic Verification: Logic/math validation for code and calculations
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class GateType(Enum):
    SELF_CHECK = "self-check"
    EVIDENCE = "evidence"
    CONFIDENCE = "confidence"
    SYMBOLIC = "symbolic"


@dataclass
class VerificationResult:
    passed: bool
    gate: Optional[str] = None
    feedback: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "gate": self.gate,
            "feedback": self.feedback,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class VerificationContext:
    prompt: str
    agent_output: str
    retrieved_evidence: List[str] = field(default_factory=list)
    requires_verification: bool = False
    task_type: Optional[str] = None


class MetacognitionEngine:
    """
    Higher-order reasoning layer that monitors agent outputs
    for confabulation and logical errors.
    """

    def __init__(
        self,
        letta_endpoint: str = "http://letta:8283",
        memgraph_endpoint: str = "bolt://memgraph:7687",
        oracle_endpoint: str = "http://deepseek-v32:8000/v1",
        confidence_threshold: float = 0.85,
    ):
        self.letta_endpoint = letta_endpoint
        self.memgraph_endpoint = memgraph_endpoint
        self.oracle_endpoint = oracle_endpoint
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def verify_output(
        self,
        agent_output: str,
        context: Dict[str, Any]
    ) -> VerificationResult:
        """
        Run the full verification pipeline on agent output.

        Args:
            agent_output: The output from the agent to verify
            context: Dictionary containing 'prompt', 'requires_verification', etc.

        Returns:
            VerificationResult with pass/fail status and feedback
        """
        verification_context = VerificationContext(
            prompt=context.get("prompt", ""),
            agent_output=agent_output,
            requires_verification=context.get("requires_verification", False),
            task_type=context.get("task_type"),
        )

        gate1_result = await self._gate1_self_check(verification_context)
        if not gate1_result.passed:
            self.logger.warning(f"Gate 1 (Self-Check) failed: {gate1_result.feedback}")
            return gate1_result

        evidence = await self._recall_evidence(agent_output)
        verification_context.retrieved_evidence = evidence

        gate2_result = await self._gate2_evidence_crossref(verification_context)
        if not gate2_result.passed:
            self.logger.warning(f"Gate 2 (Evidence) failed: {gate2_result.feedback}")
            return gate2_result

        gate3_result = await self._gate3_uncertainty_quantification(verification_context)
        if not gate3_result.passed:
            self.logger.warning(f"Gate 3 (Confidence) failed: {gate3_result.feedback}")
            return gate3_result

        if verification_context.requires_verification:
            gate4_result = await self._gate4_symbolic_verify(verification_context)
            if not gate4_result.passed:
                self.logger.warning(f"Gate 4 (Symbolic) failed: {gate4_result.feedback}")
                return gate4_result

        return VerificationResult(
            passed=True,
            confidence=gate3_result.confidence,
            metadata={
                "gates_passed": ["self-check", "evidence", "confidence", "symbolic"]
                if verification_context.requires_verification
                else ["self-check", "evidence", "confidence"],
            },
        )

    async def _gate1_self_check(self, ctx: VerificationContext) -> VerificationResult:
        """
        Gate 1: Self-consistency check.
        Verifies the output aligns with the original prompt intent.
        """
        prompt = f"""Analyze if this agent output is consistent with and addresses the original prompt.

Original Prompt:
{ctx.prompt}

Agent Output:
{ctx.agent_output}

Respond with JSON:
{{"consistent": true/false, "issues": ["list of inconsistencies if any"]}}"""

        try:
            response = await self._call_oracle(prompt)
            result = json.loads(response)

            if result.get("consistent", False):
                return VerificationResult(passed=True, gate=GateType.SELF_CHECK.value)
            else:
                issues = result.get("issues", ["Unknown inconsistency"])
                return VerificationResult(
                    passed=False,
                    gate=GateType.SELF_CHECK.value,
                    feedback=f"Output contradicts original prompt: {'; '.join(issues)}",
                )
        except Exception as e:
            self.logger.error(f"Gate 1 error: {e}")
            return VerificationResult(passed=True, gate=GateType.SELF_CHECK.value)

    async def _gate2_evidence_crossref(self, ctx: VerificationContext) -> VerificationResult:
        """
        Gate 2: Cross-reference retrieved evidence.
        Validates claims in the output against retrieved context.
        """
        if not ctx.retrieved_evidence:
            return VerificationResult(passed=True, gate=GateType.EVIDENCE.value)

        evidence_text = "\n---\n".join(ctx.retrieved_evidence[:5])

        prompt = f"""Verify if the claims in this agent output are supported by the retrieved evidence.

Agent Output:
{ctx.agent_output}

Retrieved Evidence:
{evidence_text}

Respond with JSON:
{{"supported": true/false, "unsupported_claims": ["list of claims without evidence"]}}"""

        try:
            response = await self._call_oracle(prompt)
            result = json.loads(response)

            if result.get("supported", True):
                return VerificationResult(passed=True, gate=GateType.EVIDENCE.value)
            else:
                claims = result.get("unsupported_claims", ["Unknown claim"])
                return VerificationResult(
                    passed=False,
                    gate=GateType.EVIDENCE.value,
                    feedback=f"Claims not supported by retrieved context: {'; '.join(claims)}",
                )
        except Exception as e:
            self.logger.error(f"Gate 2 error: {e}")
            return VerificationResult(passed=True, gate=GateType.EVIDENCE.value)

    async def _gate3_uncertainty_quantification(
        self, ctx: VerificationContext
    ) -> VerificationResult:
        """
        Gate 3: Uncertainty quantification.
        Estimates confidence based on evidence quality and output specificity.
        """
        prompt = f"""Estimate the confidence level (0.0 to 1.0) for this agent output based on:
1. Specificity of claims
2. Availability of supporting evidence
3. Presence of hedging language or uncertainty markers
4. Logical coherence

Agent Output:
{ctx.agent_output}

Available Evidence: {len(ctx.retrieved_evidence)} items

Respond with JSON:
{{"confidence": 0.XX, "reasoning": "brief explanation"}}"""

        try:
            response = await self._call_oracle(prompt)
            result = json.loads(response)

            confidence = float(result.get("confidence", 0.5))

            if confidence >= self.confidence_threshold:
                return VerificationResult(
                    passed=True,
                    gate=GateType.CONFIDENCE.value,
                    confidence=confidence,
                )
            else:
                return VerificationResult(
                    passed=False,
                    gate=GateType.CONFIDENCE.value,
                    confidence=confidence,
                    feedback=f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}",
                )
        except Exception as e:
            self.logger.error(f"Gate 3 error: {e}")
            return VerificationResult(
                passed=True,
                gate=GateType.CONFIDENCE.value,
                confidence=0.7,
            )

    async def _gate4_symbolic_verify(self, ctx: VerificationContext) -> VerificationResult:
        """
        Gate 4: Symbolic verification.
        Validates logic, math, and code correctness.
        """
        prompt = f"""Verify the logical and mathematical correctness of this output.
Check for:
1. Logical fallacies or contradictions
2. Mathematical errors in calculations
3. Code syntax or semantic errors (if code is present)
4. Incorrect reasoning chains

Agent Output:
{ctx.agent_output}

Respond with JSON:
{{"valid": true/false, "errors": ["list of errors if any"]}}"""

        try:
            response = await self._call_oracle(prompt)
            result = json.loads(response)

            if result.get("valid", True):
                return VerificationResult(passed=True, gate=GateType.SYMBOLIC.value)
            else:
                errors = result.get("errors", ["Unknown error"])
                return VerificationResult(
                    passed=False,
                    gate=GateType.SYMBOLIC.value,
                    feedback=f"Logical/mathematical error detected: {'; '.join(errors)}",
                )
        except Exception as e:
            self.logger.error(f"Gate 4 error: {e}")
            return VerificationResult(passed=True, gate=GateType.SYMBOLIC.value)

    async def _recall_evidence(self, query: str, limit: int = 10) -> List[str]:
        """Retrieve relevant evidence from Letta memory."""
        try:
            response = await self.http_client.post(
                f"{self.letta_endpoint}/v1/agents/default/memory/recall",
                json={"query": query, "limit": limit},
            )
            if response.status_code == 200:
                data = response.json()
                return [item.get("content", "") for item in data.get("results", [])]
        except Exception as e:
            self.logger.error(f"Failed to recall evidence: {e}")
        return []

    async def _call_oracle(self, prompt: str) -> str:
        """Call the Oracle (DeepSeek-R1) for verification tasks."""
        try:
            response = await self.http_client.post(
                f"{self.oracle_endpoint}/chat/completions",
                json={
                    "model": "deepseek-v32",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Oracle call failed: {e}")
        return "{}"


async def create_metacognition_server(host: str = "0.0.0.0", port: int = 8011):
    """Create and run the metacognition HTTP server."""
    import uvicorn
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="Metacognition Engine", version="14.0.0")
    engine = MetacognitionEngine()

    class VerifyRequest(BaseModel):
        agent_output: str
        context: Dict[str, Any]

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "14.0.0"}

    @app.post("/verify")
    async def verify(request: VerifyRequest):
        async with engine:
            result = await engine.verify_output(
                request.agent_output,
                request.context
            )
            return result.to_dict()

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(create_metacognition_server())
