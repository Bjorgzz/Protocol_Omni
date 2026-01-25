"""
Memory Nodes (Phase 4.3)

Retrieve and store memories via Mem0.
"""

import logging
import os
from typing import Any, Dict

from .state import ComplexityLevel, GraphState

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.graph.memory")
    TRACING_ENABLED = True
except ImportError:
    tracer = None
    TRACING_ENABLED = False

logger = logging.getLogger("omni.graph.memory")

# Lazy import to avoid circular dependencies
_mem0_client = None


def _get_mem0_client():
    """Get or create the Mem0 client singleton."""
    global _mem0_client
    if _mem0_client is None:
        from memory.mem0_client import Mem0Client
        # v16.2.4: Internal Docker port is 8000, external is 8050
        _mem0_client = Mem0Client(
            base_url=os.getenv("MEM0_URL", "http://mem0:8000")
        )
    return _mem0_client


async def retrieve_memory(state: GraphState) -> Dict[str, Any]:
    """
    Retrieve relevant memories from Mem0.

    Only runs for COMPLEX and TOOL_HEAVY tasks.

    Returns:
        State update with memories and memory_context
    """
    complexity = state.get("complexity")
    prompt = state.get("prompt", "")
    user_id = state.get("user_id", "default")

    # Skip memory retrieval for trivial/routine tasks
    if complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.ROUTINE):
        logger.debug("Skipping memory retrieval for non-complex task")
        return {"memories": [], "memory_context": ""}

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("retrieve_memory") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("complexity", complexity.value if complexity else "unknown")
            return await _retrieve_memory_impl(prompt, user_id, span)
    else:
        return await _retrieve_memory_impl(prompt, user_id, None)


async def _retrieve_memory_impl(prompt: str, user_id: str, span: Any) -> Dict[str, Any]:
    """Internal implementation of memory retrieval."""
    try:
        client = _get_mem0_client()

        # Check health first
        if not await client.health_check():
            logger.warning("Mem0 unhealthy, skipping memory retrieval")
            if span:
                span.set_attribute("mem0_available", False)
            return {"memories": [], "memory_context": ""}

        # Search for relevant memories
        result = await client.search_memory(
            query=prompt,
            user_id=user_id,
            limit=5,
        )

        # Format memories for context
        memories_data = [
            {"id": m.id, "content": m.content, "score": m.score}
            for m in result.memories
        ]

        # Build context string
        if result.memories:
            from memory.mem0_client import format_memories_for_context
            memory_context = format_memories_for_context(result.memories)
        else:
            memory_context = ""

        if span:
            span.set_attribute("memories_found", len(result.memories))
            span.set_attribute("mem0_available", True)

        logger.info(f"Retrieved {len(result.memories)} memories for user {user_id}")

        return {
            "memories": memories_data,
            "memory_context": memory_context,
        }

    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        if span:
            span.set_attribute("error", str(e))
        return {"memories": [], "memory_context": ""}


async def store_memory(state: GraphState) -> Dict[str, Any]:
    """
    Store the interaction in Mem0.

    Only runs for COMPLEX and TOOL_HEAVY tasks with successful responses.

    Returns:
        Empty state update (memory storage is fire-and-forget)
    """
    complexity = state.get("complexity")
    prompt = state.get("prompt", "")
    response = state.get("response", "")
    user_id = state.get("user_id", "default")

    # Skip for trivial/routine or failed responses
    if complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.ROUTINE):
        return {}

    if not response or state.get("error"):
        return {}

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("store_memory") as span:
            span.set_attribute("user_id", user_id)
            await _store_memory_impl(prompt, response, user_id, span)
    else:
        await _store_memory_impl(prompt, response, user_id, None)

    return {}


async def _store_memory_impl(prompt: str, response: str, user_id: str, span: Any) -> None:
    """Internal implementation of memory storage."""
    try:
        client = _get_mem0_client()

        # Store the interaction as a memory
        # Mem0 will extract relevant facts automatically
        content = f"User asked: {prompt[:500]}\n\nAssistant response summary: {response[:500]}"

        memory_id = await client.store_memory(
            content=content,
            user_id=user_id,
            metadata={
                "source": "cognitive_graph",
                "prompt_length": len(prompt),
                "response_length": len(response),
            },
        )

        if span:
            span.set_attribute("memory_id", memory_id or "failed")
            span.set_attribute("stored", memory_id is not None)

        if memory_id:
            logger.debug(f"Stored memory {memory_id} for user {user_id}")

    except Exception as e:
        logger.error(f"Memory storage failed: {e}")
        if span:
            span.set_attribute("error", str(e))
