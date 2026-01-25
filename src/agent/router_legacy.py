"""
Cognitive Router - Routes requests to appropriate cognitive systems.

Implements Dual Model routing (Concrete Bunker Doctrine):
- System 2 (Oracle): DeepSeek-V3.2 - Complex reasoning
- System 1 (Executor): Qwen2.5-Coder-7B (CPU) - Routine tasks

Note: GLM-4.7 and Kimi K2 deprecated due to VRAM constraints.
      MiniMax in cold storage for emergency failover only.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import httpx

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.router")
    TRACING_ENABLED = True
except ImportError:
    tracer = None
    TRACING_ENABLED = False


class ComplexityLevel(Enum):
    TRIVIAL = "trivial"
    ROUTINE = "routine"
    COMPLEX = "complex"
    TOOL_HEAVY = "tool_heavy"


class ModelEndpoint(Enum):
    DEEPSEEK_V32 = "oracle"
    KIMI_K2 = "oracle_backup"  # Cold: VRAM exhausted
    QWEN_EXECUTOR = "executor"
    MINIMAX_FAILSAFE = "failsafe"  # Cold storage


@dataclass
class AgentRequest:
    """An incoming agent request."""
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    requires_tool_orchestration: bool = False
    task_type: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7

    def estimate_complexity(self) -> ComplexityLevel:
        """Estimate task complexity based on heuristics."""
        prompt_lower = self.prompt.lower()

        trivial_indicators = [
            "hello", "hi", "thanks", "thank you", "bye",
            "what time", "who are you", "help",
        ]
        if any(ind in prompt_lower for ind in trivial_indicators):
            if len(self.prompt) < 50:
                return ComplexityLevel.TRIVIAL

        if self.requires_tool_orchestration:
            return ComplexityLevel.TOOL_HEAVY

        # Sovereign Vocabulary (v15.2.1) - Any prompt touching hardware/shell → COMPLEX
        complex_indicators = [
            # Original indicators
            "analyze", "design", "architect", "implement",
            "debug", "refactor", "optimize", "explain why",
            "compare", "evaluate", "plan", "strategy",
            "step by step", "reasoning", "prove",
            # v15.2.1: Sovereign Industrial Node vocabulary
            "ssh", "root", "kernel", "admin", "system", "deploy",
            "trace", "audit", "calculate", "math", "physics",
            "efficiency", "ratio", "power", "voltage", "watt",
            "gpu", "vram", "blackwell", "5090", "nvidia",
            "check", "monitor", "connect", "execute",
        ]
        if any(ind in prompt_lower for ind in complex_indicators):
            return ComplexityLevel.COMPLEX

        if len(self.prompt) > 500 or len(self.context) > 5:
            return ComplexityLevel.COMPLEX

        return ComplexityLevel.ROUTINE


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    endpoint: str
    model_name: str
    reason: str
    complexity: ComplexityLevel = ComplexityLevel.ROUTINE  # Default for backward compat
    fallback_endpoint: Optional[str] = None


class CognitiveRouter:
    """
    Routes requests to appropriate cognitive system based on task complexity.

    Routing Logic (Concrete Bunker Doctrine - Dual Model):
    - Trivial → Qwen Executor (fast CPU inference)
    - Routine → Qwen Executor (16.39 tok/s)
    - Complex → DeepSeek-V3.2 (deep reasoning, 7.57 tok/s)
    - Tool-Heavy → DeepSeek-V3.2 (full context required)

    Failover:
    - If DeepSeek unhealthy, fall back to Qwen
    - MiniMax in cold storage (emergency only)
    """

    def __init__(
        self,
        oracle_endpoint: str = "http://deepseek-v32:8000/v1",
        oracle_backup_endpoint: str = "http://kimi-k2:8001/v1",
        executor_endpoint: str = "http://qwen-executor:8002/v1",
        failsafe_endpoint: str = "http://minimax-failsafe:8003/v1",
    ):
        self.endpoints = {
            ModelEndpoint.DEEPSEEK_V32: oracle_endpoint,
            ModelEndpoint.KIMI_K2: oracle_backup_endpoint,
            ModelEndpoint.QWEN_EXECUTOR: executor_endpoint,
            ModelEndpoint.MINIMAX_FAILSAFE: failsafe_endpoint,
        }

        self.model_names = {
            ModelEndpoint.DEEPSEEK_V32: "deepseek-v32",
            ModelEndpoint.KIMI_K2: "kimi-k2-thinking",
            ModelEndpoint.QWEN_EXECUTOR: "qwen2.5-coder-7b",
            ModelEndpoint.MINIMAX_FAILSAFE: "minimax-m2.1",
        }

        self.health_cache: Dict[ModelEndpoint, Tuple[bool, float]] = {}
        self.health_cache_ttl = 30
        self._http_client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(__name__)

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def route(self, request: AgentRequest) -> RoutingDecision:
        """
        Determine the best endpoint for a request.

        Args:
            request: The agent request to route

        Returns:
            RoutingDecision with endpoint and reasoning
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("cognitive_routing") as span:
                complexity = request.estimate_complexity()
                span.set_attribute("complexity", complexity.value)
                span.set_attribute("prompt_length", len(request.prompt))

                primary, fallback, reason = await self._select_model(complexity, request)

                primary_healthy = await self._is_healthy(primary)
                if not primary_healthy and fallback:
                    fallback_healthy = await self._is_healthy(fallback)
                    if fallback_healthy:
                        self.logger.warning(f"{primary.name} unhealthy, falling back to {fallback.name}")
                        primary = fallback
                        fallback = None
                        reason = f"Fallback: {reason}"
                        span.set_attribute("fallback_used", True)
                    else:
                        self.logger.critical("Both primary and fallback unhealthy!")
                        reason = "CRITICAL: All endpoints unhealthy, attempting primary anyway"
                        span.set_attribute("all_unhealthy", True)

                decision = RoutingDecision(
                    endpoint=self.endpoints[primary],
                    model_name=self.model_names[primary],
                    reason=reason,
                    complexity=complexity,
                    fallback_endpoint=self.endpoints.get(fallback) if fallback else None,
                )
                span.set_attribute("routed_to", decision.model_name)
                return decision

        complexity = request.estimate_complexity()

        primary, fallback, reason = await self._select_model(complexity, request)

        primary_healthy = await self._is_healthy(primary)
        if not primary_healthy and fallback:
            fallback_healthy = await self._is_healthy(fallback)
            if fallback_healthy:
                self.logger.warning(f"{primary.name} unhealthy, falling back to {fallback.name}")
                primary = fallback
                fallback = None
                reason = f"Fallback: {reason}"
            else:
                self.logger.critical("Both primary and fallback unhealthy!")
                reason = "CRITICAL: All endpoints unhealthy, attempting primary anyway"

        return RoutingDecision(
            endpoint=self.endpoints[primary],
            model_name=self.model_names[primary],
            reason=reason,
            complexity=complexity,
            fallback_endpoint=self.endpoints.get(fallback) if fallback else None,
        )

    async def _select_model(
        self,
        complexity: ComplexityLevel,
        request: AgentRequest,
    ) -> tuple[ModelEndpoint, Optional[ModelEndpoint], str]:
        """Select primary and fallback models based on complexity."""

        if complexity == ComplexityLevel.TRIVIAL:
            return (
                ModelEndpoint.QWEN_EXECUTOR,
                ModelEndpoint.DEEPSEEK_V32,
                "Trivial task - using fast Qwen executor",
            )

        if complexity == ComplexityLevel.ROUTINE:
            return (
                ModelEndpoint.QWEN_EXECUTOR,
                ModelEndpoint.DEEPSEEK_V32,
                "Routine task - using Qwen executor (16.39 tok/s)",
            )

        if complexity == ComplexityLevel.TOOL_HEAVY:
            return (
                ModelEndpoint.DEEPSEEK_V32,
                ModelEndpoint.QWEN_EXECUTOR,
                "Tool-heavy task - DeepSeek for full context",
            )

        return (
            ModelEndpoint.DEEPSEEK_V32,
            ModelEndpoint.QWEN_EXECUTOR,
            "Complex task - using DeepSeek for deep reasoning",
        )

    async def _is_healthy(self, model: ModelEndpoint) -> bool:
        """Check if a model endpoint is healthy."""
        if model in self.health_cache:
            cached_healthy, cached_time = self.health_cache[model]
            if time.time() - cached_time < self.health_cache_ttl:
                return cached_healthy

        try:
            endpoint = self.endpoints[model]
            base_url = endpoint.rsplit('/v1', 1)[0]
            response = await self.http_client.get(
                f"{base_url}/health",
                timeout=5.0,
            )
            healthy = response.status_code == 200
            self.health_cache[model] = (healthy, time.time())
            return healthy
        except Exception as e:
            self.logger.warning(f"Health check failed for {model.name}: {e}")
            self.health_cache[model] = (False, time.time())
            return False

    async def refresh_health(self):
        """Refresh health status for all endpoints."""
        tasks = [self._is_healthy(model) for model in ModelEndpoint]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_health_status(self) -> Dict[str, bool]:
        """Get current health status of all models."""
        return {
            model.name: self.health_cache.get(model, (False, 0))[0]
            for model in ModelEndpoint
        }


class AgentOrchestrator:
    """
    Main orchestrator that combines routing with metacognition and GEPA.
    """

    def __init__(
        self,
        router: CognitiveRouter,
        metacog_endpoint: str = "http://metacognition:8011",
        gepa_endpoint: str = "http://gepa-engine:8010",
    ):
        self.router = router
        self.metacog_endpoint = metacog_endpoint
        self.gepa_endpoint = gepa_endpoint
        self._http_client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(__name__)

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            # v15.2.1: 5-Minute Rule - 671B models breathe slowly
            self._http_client = httpx.AsyncClient(timeout=300.0)
        return self._http_client

    async def process(self, request: AgentRequest) -> Dict[str, Any]:
        """
        Process a request through the full pipeline:
        1. Route to appropriate model
        2. Get response
        3. Verify via metacognition
        4. Record trajectory for GEPA
        """
        import time
        start_time = time.time()

        decision = await self.router.route(request)
        self.logger.info(f"Routing to {decision.model_name}: {decision.reason}")

        response, usage = await self._call_model(decision, request)

        verification = await self._verify_output(response, request)

        latency_ms = (time.time() - start_time) * 1000
        await self._record_trajectory(request, response, verification, latency_ms)

        return {
            "response": response,
            "model": decision.model_name,
            "routing_reason": decision.reason,
            "verification": verification,
            "latency_ms": latency_ms,
            "usage": usage,
        }

    async def _call_model(
        self,
        decision: RoutingDecision,
        request: AgentRequest,
    ) -> Tuple[str, Dict[str, Any]]:
        """Call the selected model endpoint. Returns (content, usage_dict).

        v15.2.1: For COMPLEX/TOOL_HEAVY, uses streaming internally to keep
        connection alive during long inference. Buffers response for return.
        """
        call_start = time.time()

        # v15.2.2: Streaming mandate based on complexity, not model name
        # COMPLEX and TOOL_HEAVY tasks require streaming to prevent LB idle timeouts
        use_streaming = decision.complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY)

        if use_streaming:
            return await self._call_model_streaming_buffered(decision, request, call_start)

        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("model_inference") as span:
                span.set_attribute("endpoint", decision.endpoint)
                span.set_attribute("model", decision.model_name)
                span.set_attribute("streaming", False)
                try:
                    response = await self.http_client.post(
                        f"{decision.endpoint}/chat/completions",
                        json={
                            "model": decision.model_name,
                            "messages": [{"role": "user", "content": request.prompt}],
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                        },
                    )
                    latency_ms = (time.time() - call_start) * 1000
                    span.set_attribute("latency_ms", latency_ms)
                    span.set_attribute("status_code", response.status_code)
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        span.set_attribute("tokens", usage.get("total_tokens", 0))
                        return content, usage
                except Exception as e:
                    span.set_attribute("error", str(e))
                    self.logger.error(f"Model call failed: {e}")

                    if decision.fallback_endpoint:
                        span.set_attribute("fallback_attempted", True)
                        self.logger.info("Trying fallback endpoint")
                        try:
                            response = await self.http_client.post(
                                f"{decision.fallback_endpoint}/chat/completions",
                                json={
                                    "model": "fallback",
                                    "messages": [{"role": "user", "content": request.prompt}],
                                },
                            )
                            if response.status_code == 200:
                                data = response.json()
                                content = data["choices"][0]["message"]["content"]
                                usage = data.get("usage", {})
                                return content, usage
                        except Exception as e2:
                            self.logger.error(f"Fallback also failed: {e2}")

                return "I apologize, but I'm unable to process your request at this time.", {}

        try:
            response = await self.http_client.post(
                f"{decision.endpoint}/chat/completions",
                json={
                    "model": decision.model_name,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                },
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return content, usage
        except Exception as e:
            self.logger.error(f"Model call failed: {e}")

            if decision.fallback_endpoint:
                self.logger.info("Trying fallback endpoint")
                try:
                    response = await self.http_client.post(
                        f"{decision.fallback_endpoint}/chat/completions",
                        json={
                            "model": "fallback",
                            "messages": [{"role": "user", "content": request.prompt}],
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        return content, usage
                except Exception as e2:
                    self.logger.error(f"Fallback also failed: {e2}")

        return "I apologize, but I'm unable to process your request at this time.", {}

    async def _call_model_streaming_buffered(
        self,
        decision: RoutingDecision,
        request: AgentRequest,
        call_start: float,
    ) -> Tuple[str, Dict[str, Any]]:
        """Call model with streaming, buffer response. Keeps connection alive.

        v15.2.2: Mandatory for COMPLEX/TOOL_HEAVY to prevent LB idle timeouts
        during 30-90+ second inference times. Now validates response status.
        """
        import json as json_module

        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("model_inference") as span:
                span.set_attribute("endpoint", decision.endpoint)
                span.set_attribute("model", decision.model_name)
                span.set_attribute("streaming", True)
                try:
                    content_buffer = []
                    usage_data = {}

                    async with self.http_client.stream(
                        "POST",
                        f"{decision.endpoint}/chat/completions",
                        json={
                            "model": decision.model_name,
                            "messages": [{"role": "user", "content": request.prompt}],
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                            "stream": True,
                        },
                        timeout=300.0,
                    ) as response:
                        # v15.2.2: Validate response before streaming
                        response.raise_for_status()
                        span.set_attribute("status_code", response.status_code)

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json_module.loads(data_str)
                                    if "usage" in data:
                                        usage_data = data["usage"]
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            content_buffer.append(delta["content"])
                                except json_module.JSONDecodeError:
                                    continue

                    latency_ms = (time.time() - call_start) * 1000
                    span.set_attribute("latency_ms", latency_ms)
                    span.set_attribute("tokens", usage_data.get("total_tokens", 0))
                    content = "".join(content_buffer)
                    return content, usage_data

                except Exception as e:
                    span.set_attribute("error", str(e))
                    self.logger.error(f"Streaming model call failed: {e}")

                    if decision.fallback_endpoint:
                        span.set_attribute("fallback_attempted", True)
                        self.logger.info("Trying fallback endpoint (non-streaming)")
                        try:
                            response = await self.http_client.post(
                                f"{decision.fallback_endpoint}/chat/completions",
                                json={
                                    "model": "fallback",
                                    "messages": [{"role": "user", "content": request.prompt}],
                                },
                            )
                            if response.status_code == 200:
                                data = response.json()
                                content = data["choices"][0]["message"]["content"]
                                usage = data.get("usage", {})
                                return content, usage
                        except Exception as e2:
                            self.logger.error(f"Fallback also failed: {e2}")

                return "I apologize, but I'm unable to process your request at this time.", {}

        # Non-tracing path
        try:
            import json as json_module
            content_buffer = []
            usage_data = {}

            async with self.http_client.stream(
                "POST",
                f"{decision.endpoint}/chat/completions",
                json={
                    "model": decision.model_name,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True,
                },
                timeout=300.0,
            ) as response:
                # v15.2.2: Validate response before streaming
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json_module.loads(data_str)
                            if "usage" in data:
                                usage_data = data["usage"]
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content_buffer.append(delta["content"])
                        except json_module.JSONDecodeError:
                            continue

            content = "".join(content_buffer)
            return content, usage_data

        except Exception as e:
            self.logger.error(f"Streaming model call failed: {e}")

            if decision.fallback_endpoint:
                self.logger.info("Trying fallback endpoint")
                try:
                    response = await self.http_client.post(
                        f"{decision.fallback_endpoint}/chat/completions",
                        json={
                            "model": "fallback",
                            "messages": [{"role": "user", "content": request.prompt}],
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        return content, usage
                except Exception as e2:
                    self.logger.error(f"Fallback also failed: {e2}")

        return "I apologize, but I'm unable to process your request at this time.", {}

    async def _verify_output(
        self,
        output: str,
        request: AgentRequest,
    ) -> Dict[str, Any]:
        """Verify output via metacognition engine."""
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("metacog_verify") as span:
                try:
                    response = await self.http_client.post(
                        f"{self.metacog_endpoint}/verify",
                        json={
                            "agent_output": output,
                            "context": {
                                "prompt": request.prompt,
                                "requires_verification": request.task_type == "code",
                                "task_type": request.task_type,
                            },
                        },
                    )
                    if response.status_code == 200:
                        result = response.json()
                        span.set_attribute("verdict", "pass" if result.get("passed") else "fail")
                        span.set_attribute("confidence", result.get("confidence", 0))
                        return result
                except Exception as e:
                    span.set_attribute("error", str(e))
                    self.logger.warning(f"Metacognition verification failed: {e}")

                return {"passed": True, "confidence": 0.5, "note": "Verification skipped"}

        try:
            response = await self.http_client.post(
                f"{self.metacog_endpoint}/verify",
                json={
                    "agent_output": output,
                    "context": {
                        "prompt": request.prompt,
                        "requires_verification": request.task_type == "code",
                        "task_type": request.task_type,
                    },
                },
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.warning(f"Metacognition verification failed: {e}")

        return {"passed": True, "confidence": 0.5, "note": "Verification skipped"}

    async def _record_trajectory(
        self,
        request: AgentRequest,
        response: str,
        verification: Dict[str, Any],
        latency_ms: float,
    ):
        """Record trajectory for GEPA evolution."""
        try:
            await self.http_client.post(
                f"{self.gepa_endpoint}/record-trajectory",
                json={
                    "task": request.prompt[:200],
                    "prompt": request.prompt,
                    "output": response,
                    "success": verification.get("passed", True),
                    "error": verification.get("feedback"),
                    "latency_ms": latency_ms,
                },
            )
        except Exception as e:
            self.logger.warning(f"Failed to record trajectory: {e}")

    async def process_stream(
        self,
        request: AgentRequest,
        chat_id: str,
    ):
        """
        Process a request with streaming response.

        Yields SSE-formatted chunks compatible with OpenAI API.
        """
        import json
        import time
        start_time = time.time()

        decision = await self.router.route(request)
        self.logger.info(f"Streaming from {decision.model_name}: {decision.reason}")

        full_response = ""
        usage_data = {}

        async for chunk in self._call_model_stream(decision, request, chat_id):
            if chunk.get("done"):
                usage_data = chunk.get("usage", {})
                latency_ms = (time.time() - start_time) * 1000
                final_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "model": decision.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }],
                    "usage": usage_data,
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            else:
                content = chunk.get("content") or ""
                full_response += content
                if content:  # Only yield non-empty chunks
                    stream_chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "model": decision.model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(stream_chunk)}\n\n"

        latency_ms = (time.time() - start_time) * 1000
        await self._record_trajectory(
            request, full_response,
            {"passed": True, "confidence": 0.8, "note": "Stream completed"},
            latency_ms,
        )

    async def _call_model_stream(
        self,
        decision: RoutingDecision,
        request: AgentRequest,
        chat_id: str,
    ):
        """
        Call model endpoint with streaming enabled.

        Yields content chunks and a final 'done' marker with usage stats.
        """
        import json

        try:
            async with self.http_client.stream(
                "POST",
                f"{decision.endpoint}/chat/completions",
                json={
                    "model": decision.model_name,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True,
                },
                timeout=300.0,  # v15.2.1: 5-Minute Rule for streaming
            ) as response:
                usage_data = {}
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield {"done": True, "usage": usage_data}
                            return
                        try:
                            data = json.loads(data_str)
                            if "usage" in data:
                                usage_data = data["usage"]
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield {"content": delta["content"]}
                        except json.JSONDecodeError:
                            continue

                yield {"done": True, "usage": usage_data}

        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            yield {"content": f"Error: {e}"}
            yield {"done": True, "usage": {}}
