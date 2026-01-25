"""
Status Node (v16.3.3 - Operation Internalize Part 3)

LangGraph node that handles self-introspection queries.
Short-circuits the normal model call for status/VRAM queries.
"""

import asyncio
import logging
import os
from typing import Any, Dict

from ..tools.status import get_sovereign_status, format_status_for_agent

logger = logging.getLogger("omni.graph.nodes.status")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.graph.nodes.status") if TRACING_ENABLED else None
except ImportError:
    tracer = None


async def handle_status(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle status queries by calling the sovereign status tool.
    
    This node short-circuits the normal model call path when the prompt
    is detected as a status/introspection query.
    
    Returns:
        State update with formatted status response
    """
    logger.info("Handling sovereign status query")
    
    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("handle_status") as span:
            status = await asyncio.to_thread(get_sovereign_status)
            span.set_attribute("overall_status", status.get("status", "unknown"))
            span.set_attribute("gpu_count", status.get("summary", {}).get("gpu_count", 0))
            span.set_attribute("memories", status.get("summary", {}).get("memories", 0))
    else:
        status = await asyncio.to_thread(get_sovereign_status)
    
    formatted_response = format_status_for_agent(status)
    
    return {
        "response": formatted_response,
        "model_name": "sovereign-introspection",
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "latency_ms": 0,
        "raw_status": status,
    }


def is_status_query(prompt: str) -> bool:
    """
    Detect if the prompt is asking about system status.
    
    Returns True if the prompt contains status-related keywords and appears
    to be asking for introspection rather than general knowledge.
    """
    prompt_lower = prompt.lower()
    
    status_keywords = [
        "status", "vram", "gpu status", "memory status",
        "health report", "system status", "how is your",
        "how much vram", "gpu memory", "your vram",
        "introspect", "self-check", "sovereign status",
    ]
    
    for keyword in status_keywords:
        if keyword in prompt_lower:
            return True
    
    return False
