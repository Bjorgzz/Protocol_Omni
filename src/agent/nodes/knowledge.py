"""
Knowledge Node (Phase 4.4)

LangGraph node for retrieving code context from Memgraph.
"""

import logging
import os
from typing import Any, Dict

from .state import ComplexityLevel, GraphState

logger = logging.getLogger("omni.agent.nodes.knowledge")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.agent.nodes.knowledge") if TRACING_ENABLED else None
except ImportError:
    tracer = None

_memgraph_client = None


def _get_memgraph_client():
    """Lazy initialization of Memgraph client."""
    global _memgraph_client
    if _memgraph_client is None:
        try:
            from knowledge.memgraph_client import MemgraphClient
            _memgraph_client = MemgraphClient()
        except Exception as e:
            logger.error(f"Failed to initialize Memgraph client: {e}")
            return None
    return _memgraph_client


def should_retrieve_knowledge(state: GraphState) -> bool:
    """
    Determine if knowledge graph retrieval should run.

    Only runs for TOOL_HEAVY tasks with code-related queries.
    """
    complexity = state.get("complexity")

    if complexity != ComplexityLevel.TOOL_HEAVY:
        return False

    prompt = state.get("prompt", "").lower()

    code_indicators = [
        "function", "class", "method", "import", "file",
        "where is", "find", "reference", "caller", "called",
        "defined", "implement", "code", "source",
    ]

    return any(ind in prompt for ind in code_indicators)


async def retrieve_knowledge(state: GraphState) -> Dict[str, Any]:
    """
    Retrieve code context from Memgraph knowledge graph.

    Only runs for TOOL_HEAVY tasks with code-related queries.

    Returns: State update with code_context
    """
    if not should_retrieve_knowledge(state):
        return {"code_context": ""}

    prompt = state.get("prompt", "")

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("retrieve_knowledge") as span:
            span.set_attribute("prompt_length", len(prompt))
            return await _retrieve_knowledge_impl(prompt, span)
    else:
        return await _retrieve_knowledge_impl(prompt, None)


async def _retrieve_knowledge_impl(prompt: str, span: Any) -> Dict[str, Any]:
    """Internal implementation of knowledge retrieval."""
    try:
        client = _get_memgraph_client()
        if client is None:
            logger.warning("Memgraph client unavailable")
            return {"code_context": ""}

        if not client.health_check():
            logger.warning("Memgraph unhealthy, skipping knowledge retrieval")
            return {"code_context": ""}

        context = client.get_code_context(prompt, limit=10)

        code_context = context.to_prompt_context(max_chars=2000)

        if span:
            span.set_attribute("symbols_found", len(context.symbols))
            span.set_attribute("context_length", len(code_context))

        logger.info(f"Retrieved {len(context.symbols)} symbols from knowledge graph")

        return {"code_context": code_context}

    except Exception as e:
        logger.error(f"Knowledge retrieval failed: {e}")
        return {"code_context": ""}
