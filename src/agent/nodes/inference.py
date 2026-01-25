"""
Inference Node (Phase 4.3)

Model call node with HTTP client, streaming support, and OTEL instrumentation.

NOTE (v16.2.6): Using synchronous httpx.Client because AsyncClient has a known
issue with llama.cpp server returning 400 errors. Wrapped with asyncio.to_thread().
"""

import asyncio
import json as json_mod
import logging
import os
import time
from typing import Any, AsyncIterator, Dict

import httpx

from .state import ENDPOINTS, ComplexityLevel, GraphState

logger = logging.getLogger("omni.agent.nodes.inference")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.agent.nodes.inference") if TRACING_ENABLED else None
except ImportError:
    tracer = None


async def call_model(state: GraphState) -> Dict[str, Any]:
    """
    Call the appropriate model based on complexity classification.

    Uses streaming internally for COMPLEX/TOOL_HEAVY tasks to prevent
    load balancer idle timeouts (5-minute rule for 671B models).

    Returns: State update with response, usage, and latency
    """
    complexity = state.get("complexity", ComplexityLevel.ROUTINE)
    endpoint_key = "deepseek" if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY) else "qwen"
    endpoint = ENDPOINTS[endpoint_key]

    messages = state.get("messages", [])
    prompt = state.get("prompt", "")
    memory_context = state.get("memory_context", "")
    code_context = state.get("code_context", "")

    if prompt and not messages:
        messages = [{"role": "user", "content": prompt}]

    if memory_context or code_context:
        messages = _inject_context(messages, memory_context, code_context)

    use_streaming = complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY)

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("call_model") as span:
            span.set_attribute("model", endpoint.name)
            span.set_attribute("complexity", complexity.value if complexity else "unknown")
            span.set_attribute("streaming", use_streaming)
            span.set_attribute("endpoint", endpoint.url)
            return await _call_model_impl(endpoint, messages, state, use_streaming, span)
    else:
        return await _call_model_impl(endpoint, messages, state, use_streaming, None)


def _inject_context(
    messages: list,
    memory_context: str,
    code_context: str
) -> list:
    """Inject memory and code context into the system message."""
    context_parts = []

    if memory_context:
        context_parts.append(memory_context)
    if code_context:
        context_parts.append(f"<code_context>\n{code_context}\n</code_context>")

    if not context_parts:
        return messages

    context_block = "\n\n".join(context_parts)

    messages = list(messages)

    if messages and messages[0].get("role") == "system":
        messages[0] = {
            "role": "system",
            "content": f"{messages[0]['content']}\n\n{context_block}"
        }
    else:
        messages.insert(0, {"role": "system", "content": context_block})

    return messages


async def _call_model_impl(
    endpoint,
    messages: list,
    state: GraphState,
    use_streaming: bool,
    span: Any
) -> Dict[str, Any]:
    """Internal implementation of model call.
    
    Uses synchronous httpx.Client wrapped in asyncio.to_thread() because
    AsyncClient has compatibility issues with llama.cpp server (returns 400).
    """
    start_time = time.perf_counter()

    request_body = {
        "model": endpoint.model_id,
        "messages": messages,
        "temperature": state.get("temperature", 0.7),
        "max_tokens": state.get("max_tokens", 4096),
        "stream": use_streaming,
    }

    logger.info(f"[PAYLOAD AUDIT] Target: {endpoint.url}/chat/completions")
    logger.debug(f"[PAYLOAD AUDIT] Body: {json_mod.dumps(request_body, default=str)[:500]}")

    try:
        if use_streaming:
            # Streaming: use sync client in thread for compatibility
            response_text, usage = await asyncio.to_thread(
                _handle_streaming_sync, endpoint.url, request_body, endpoint.timeout
            )
        else:
            # Non-streaming: use sync client in thread
            response_text, usage = await asyncio.to_thread(
                _handle_non_streaming_sync, endpoint.url, request_body, endpoint.timeout
            )

        latency_ms = (time.perf_counter() - start_time) * 1000

        if span:
            span.set_attribute("success", True)
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("response_length", len(response_text))
            if usage:
                span.set_attribute("prompt_tokens", usage.get("prompt_tokens", 0))
                span.set_attribute("completion_tokens", usage.get("completion_tokens", 0))

        logger.info(
            f"Model call completed: {endpoint.name}, "
            f"latency={latency_ms:.0f}ms, "
            f"response_len={len(response_text)}"
        )

        return {
            "response": response_text,
            "usage": usage or {},
            "latency_ms": latency_ms,
            "model_name": endpoint.name,
        }

    except httpx.TimeoutException as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"Model timeout after {latency_ms:.0f}ms: {e}"
        logger.error(error_msg)

        if span:
            span.set_attribute("success", False)
            span.set_attribute("error", "timeout")

        return {
            "response": "",
            "error": error_msg,
            "latency_ms": latency_ms,
        }

    except httpx.HTTPStatusError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        # v16.2.6: Capture response body for debugging 400 errors
        try:
            response_body = e.response.text[:500] if e.response else "no body"
        except httpx.ResponseNotRead:
            response_body = "(streaming response - body not available)"
        error_msg = f"Model HTTP error {e.response.status_code}: {e}"
        logger.error(f"{error_msg} | Response: {response_body}")

        if span:
            span.set_attribute("success", False)
            span.set_attribute("error", f"http_{e.response.status_code}")

        return {
            "response": "",
            "error": error_msg,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"Model call failed: {e}"
        logger.error(error_msg)

        if span:
            span.set_attribute("success", False)
            span.set_attribute("error", str(type(e).__name__))

        return {
            "response": "",
            "error": error_msg,
            "latency_ms": latency_ms,
        }


def _handle_streaming_sync(
    url: str,
    request_body: dict,
    timeout: float
) -> tuple[str, dict]:
    """Handle streaming response synchronously (for asyncio.to_thread compatibility)."""
    chunks = []
    usage = {}

    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{url}/chat/completions",
            json=request_body,
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status_code >= 400:
                body = response.read()
                logger.error(f"[STREAMING ERROR] HTTP {response.status_code}: {body.decode()[:500]}")
                response.raise_for_status()

            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json_mod.loads(data)

                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunks.append(content)

                    if "usage" in chunk:
                        usage = chunk["usage"]

                except json_mod.JSONDecodeError:
                    continue

    return "".join(chunks), usage


def _handle_non_streaming_sync(
    url: str,
    request_body: dict,
    timeout: float
) -> tuple[str, dict]:
    """Handle non-streaming response synchronously."""
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{url}/chat/completions",
            json=request_body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        data = response.json()

        content = ""
        if "choices" in data and data["choices"]:
            content = data["choices"][0].get("message", {}).get("content", "")

        usage = data.get("usage", {})

        return content, usage


async def stream_model_response(state: GraphState) -> AsyncIterator[str]:
    """
    Stream model response for SSE output.

    This is used when the client requests streaming (stream: true).
    Returns an async iterator of SSE-formatted chunks.
    
    Uses synchronous httpx.Client in a thread due to AsyncClient compatibility
    issues with llama.cpp server.
    """
    complexity = state.get("complexity", ComplexityLevel.ROUTINE)
    endpoint_key = "deepseek" if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY) else "qwen"
    endpoint = ENDPOINTS[endpoint_key]

    messages = state.get("messages", [])
    prompt = state.get("prompt", "")
    memory_context = state.get("memory_context", "")
    code_context = state.get("code_context", "")

    if prompt and not messages:
        messages = [{"role": "user", "content": prompt}]

    if memory_context or code_context:
        messages = _inject_context(messages, memory_context, code_context)

    request_body = {
        "model": endpoint.model_id,
        "messages": messages,
        "temperature": state.get("temperature", 0.7),
        "max_tokens": state.get("max_tokens", 4096),
        "stream": True,
    }

    # Use sync client in thread for SSE streaming
    def stream_sync():
        lines = []
        with httpx.Client(timeout=endpoint.timeout) as client:
            with client.stream(
                "POST",
                f"{endpoint.url}/chat/completions",
                json=request_body,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        lines.append(line + "\n")
        return lines

    # Run in thread and yield results
    lines = await asyncio.to_thread(stream_sync)
    for line in lines:
        yield line
