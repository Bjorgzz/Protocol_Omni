"""
Agent Orchestrator API - FastAPI wrapper for LangGraph Cognitive Workflow

Protocol OMNI v16.3.3 - Phase 4: SOVEREIGN COGNITION
Operation Internalize Part 3: Sovereign status tool bound to cognitive graph
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .graph import get_graph_health, invoke_graph, stream_graph

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.agent.main") if TRACING_ENABLED else None
except ImportError:
    tracer = None


def _init_tracing():
    """Initialize Phoenix OTEL tracer provider."""
    phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://arize-phoenix:4317")
    try:
        from phoenix.otel import register
        tracer_provider = register(
            project_name="omni-agent",
            endpoint=phoenix_endpoint,
        )
        logger.info(f"Phoenix tracing initialized: {phoenix_endpoint}")
        return tracer_provider
    except ImportError:
        logger.warning("Phoenix OTEL not available, tracing disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Phoenix tracing: {e}")
        return None


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "auto"
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    routing_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    graph: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_tracing()

    logger.info("Protocol OMNI v16.3.3 - LangGraph Cognitive Workflow initialized")
    logger.info(f"Tracing enabled: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT') is not None}")

    yield

    logger.info("Shutting down Agent Orchestrator")


app = FastAPI(
    title="Agent Orchestrator",
    description="Protocol OMNI v16.3.3 - LangGraph Cognitive Workflow",
    version="16.3.3",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    graph_status = get_graph_health()

    return HealthResponse(
        status="healthy" if graph_status["graph_compiled"] else "degraded",
        graph=graph_status,
    )


@app.get("/health/full")
async def health_full():
    """
    Comprehensive health check with OTEL tracing.
    
    Operation Internalize (v16.3.1): Replaces scripts/test_agent_connection.py
    
    Checks:
    - Graph: LangGraph compilation status
    - Oracle: DeepSeek-V3.2 at :8000
    - Executor: Qwen at :8002
    - Memory: Mem0 at :8000
    - Routing: Mini test to verify TRIVIAL → Qwen routing
    """
    start_time = time.perf_counter()
    results: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "components": {},
        "routing_test": None,
    }
    
    def _get_base_url(env_var: str, default: str) -> str:
        """Get base URL stripping /v1 or /v1/ suffix for health checks."""
        url = os.getenv(env_var, default).rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3]
        return url
    
    oracle_url = _get_base_url("ORACLE_ENDPOINT", "http://deepseek-v32:8000")
    executor_url = _get_base_url("EXECUTOR_ENDPOINT", "http://qwen-executor:8002")
    mem0_url = _get_base_url("MEM0_URL", "http://mem0:8000")
    
    def _check_component(name: str, url: str) -> Dict[str, Any]:
        """Check a component's health endpoint."""
        health_endpoint = f"{url}/health"
        component_start = time.perf_counter()
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(health_endpoint)
                latency_ms = (time.perf_counter() - component_start) * 1000
                if resp.status_code == 200:
                    return {
                        "status": "healthy",
                        "latency_ms": round(latency_ms, 1),
                        "endpoint": health_endpoint,
                    }
                return {
                    "status": "degraded",
                    "latency_ms": round(latency_ms, 1),
                    "endpoint": health_endpoint,
                    "error": f"HTTP {resp.status_code}",
                }
        except Exception as e:
            latency_ms = (time.perf_counter() - component_start) * 1000
            return {
                "status": "unhealthy",
                "latency_ms": round(latency_ms, 1),
                "endpoint": health_endpoint,
                "error": str(e),
            }
    
    def _run_routing_test() -> Dict[str, Any]:
        """Send trivial prompt to self, verify Qwen handles it."""
        test_start = time.perf_counter()
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    "http://localhost:8080/v1/chat/completions",
                    json={
                        "model": "auto",
                        "messages": [{"role": "user", "content": "1+1"}],
                        "temperature": 0.1,
                        "max_tokens": 32,
                    },
                )
                latency_ms = (time.perf_counter() - test_start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    routed_model = data.get("model", "unknown")
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    expected_qwen = "qwen" in routed_model.lower()
                    return {
                        "status": "pass" if expected_qwen else "warn",
                        "latency_ms": round(latency_ms, 1),
                        "routed_to": routed_model,
                        "expected": "qwen",
                        "match": expected_qwen,
                        "response_preview": response_text[:50],
                    }
                return {
                    "status": "fail",
                    "latency_ms": round(latency_ms, 1),
                    "error": f"HTTP {resp.status_code}",
                }
        except Exception as e:
            latency_ms = (time.perf_counter() - test_start) * 1000
            return {
                "status": "fail",
                "latency_ms": round(latency_ms, 1),
                "error": str(e),
            }
    
    async def _run_all_checks():
        """Run all health checks concurrently."""
        loop = asyncio.get_event_loop()
        
        graph_check = get_graph_health()
        results["components"]["graph"] = {
            "status": "healthy" if graph_check["graph_compiled"] else "unhealthy",
            "tracing_enabled": graph_check.get("tracing_enabled", False),
            "nodes": len(graph_check.get("nodes", [])),
        }
        
        oracle_result, executor_result, memory_result, routing_result = await asyncio.gather(
            loop.run_in_executor(None, _check_component, "oracle", oracle_url),
            loop.run_in_executor(None, _check_component, "executor", executor_url),
            loop.run_in_executor(None, _check_component, "memory", mem0_url),
            loop.run_in_executor(None, _run_routing_test),
        )
        
        results["components"]["oracle"] = oracle_result
        results["components"]["executor"] = executor_result
        results["components"]["memory"] = memory_result
        results["routing_test"] = routing_result
        
        unhealthy = any(
            c.get("status") == "unhealthy" 
            for c in results["components"].values()
        )
        degraded = any(
            c.get("status") == "degraded" 
            for c in results["components"].values()
        )
        routing_failed = routing_result.get("status") == "fail"
        
        if unhealthy:
            results["status"] = "unhealthy"
        elif degraded or routing_failed:
            results["status"] = "degraded"
    
    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("health_full") as span:
            span.set_attribute("check.oracle_url", oracle_url)
            span.set_attribute("check.executor_url", executor_url)
            span.set_attribute("check.mem0_url", mem0_url)
            
            await _run_all_checks()
            
            total_latency = (time.perf_counter() - start_time) * 1000
            results["total_latency_ms"] = round(total_latency, 1)
            
            span.set_attribute("check.status", results["status"])
            span.set_attribute("check.total_latency_ms", total_latency)
            span.set_attribute("check.routing_match", results["routing_test"].get("match", False))
    else:
        await _run_all_checks()
        total_latency = (time.perf_counter() - start_time) * 1000
        results["total_latency_ms"] = round(total_latency, 1)
    
    return results


@app.get("/v1/status")
async def sovereign_status():
    """
    Sovereign Status - Self-introspection endpoint.
    
    Operation Internalize Part 2 (v16.3.3): Native tool for system awareness.
    
    Returns:
    - body: GPU metrics (VRAM, utilization, temperature, power)
    - mind: Memory layer status (Mem0 memory count)
    - summary: Quick overview
    """
    from .tools.status import get_sovereign_status
    
    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("sovereign_status") as span:
            result = await asyncio.to_thread(get_sovereign_status)
            span.set_attribute("status.overall", result.get("status", "unknown"))
            span.set_attribute("status.gpu_count", result.get("summary", {}).get("gpu_count", 0))
            span.set_attribute("status.memories", result.get("summary", {}).get("memories", 0))
            return result
    else:
        return await asyncio.to_thread(get_sovereign_status)


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    user_message = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        ""
    )

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.stream:
        async def generate():
            async for line in stream_graph(
                prompt=user_message,
                messages=messages,
                chat_id=chat_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                model=request.model or "auto",
            ):
                yield line

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = await invoke_graph(
        prompt=user_message,
        messages=messages,
        chat_id=chat_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        model=request.model or "auto",
    )

    response_text = result.get("response", "")
    usage_data = result.get("usage", {})
    model_name = result.get("model_name", "auto")
    routing_reason = result.get("routing_reason", "")

    if result.get("error"):
        logger.error(f"Graph error: {result['error']}")
        response_text = response_text or "I apologize, but I'm unable to process your request at this time."

    return ChatResponse(
        id=chat_id,
        created=int(time.time()),
        model=model_name,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=usage_data.get("prompt_tokens", len(user_message) // 4),
            completion_tokens=usage_data.get("completion_tokens", len(response_text) // 4),
            total_tokens=usage_data.get("total_tokens", (len(user_message) + len(response_text)) // 4),
        ),
        routing_reason=routing_reason,
    )


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "deepseek-v3.2", "object": "model", "owned_by": "omni"},
            {"id": "qwen2.5-coder-7b", "object": "model", "owned_by": "omni"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
