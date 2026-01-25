"""
LangGraph Cognitive Workflow (Phase 4.3 + 4.4 + v16.3.3)

Defines the DAG-based cognitive routing workflow using LangGraph.
Replaces custom CognitiveRouter with industry-standard graph execution.

Graph Topology:
    START → parse → memory → classify → {status | knowledge → model} → store → metacog → END
    
v16.3.3: Added status node for self-introspection queries (Operation Internalize Part 3)
"""

import logging
import os
import time
from typing import Any, AsyncIterator, Dict, Literal

from langgraph.graph import END, StateGraph

from .nodes.classification import classify_complexity
from .nodes.inference import call_model, stream_model_response
from .nodes.knowledge import retrieve_knowledge
from .nodes.memory import retrieve_memory, store_memory
from .nodes.metacognition import metacog_verify, should_verify
from .nodes.state import ComplexityLevel, GraphState
from .nodes.status import handle_status

logger = logging.getLogger("omni.agent.graph")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.agent.graph") if TRACING_ENABLED else None
except ImportError:
    tracer = None


def parse_request(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate incoming request.

    Initializes state with defaults and extracts prompt from messages.
    """
    messages = state.get("messages", [])
    prompt = state.get("prompt", "")

    if not prompt and messages:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break

    return {
        "prompt": prompt,
        "start_time": time.perf_counter(),
        "retry_count": state.get("retry_count", 0),
        "user_id": state.get("user_id", "default"),
        "chat_id": state.get("chat_id", ""),
    }


def should_use_memory(state: GraphState) -> Literal["retrieve", "skip"]:
    """
    Determine if memory retrieval should run.

    Returns 'skip' for trivial greetings to reduce latency.
    Memory is retrieved before classification to inform routing.
    """
    prompt = state.get("prompt", "").lower()

    trivial_greetings = ["hello", "hi", "hey", "thanks", "thank you", "bye"]
    if any(g in prompt for g in trivial_greetings) and len(prompt) < 50:
        return "skip"

    return "retrieve"


def route_by_complexity(state: GraphState) -> Literal["deepseek", "qwen"]:
    """
    Route to appropriate model based on complexity.
    """
    complexity = state.get("complexity", ComplexityLevel.ROUTINE)

    if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY):
        return "deepseek"

    return "qwen"


def route_after_classify(state: GraphState) -> Literal["status", "knowledge"]:
    """
    Route after classification - status queries short-circuit to status node.
    
    v16.3.3: Operation Internalize Part 3
    """
    if state.get("is_status_query", False):
        logger.info("Routing to status node (introspection query)")
        return "status"
    return "knowledge"


def should_run_metacog(state: GraphState) -> Literal["verify", "skip"]:
    """
    Determine if metacognition verification should run.
    """
    if should_verify(state):
        return "verify"
    return "skip"


def route_after_metacog(state: GraphState) -> Literal["respond", "retry"]:
    """
    Route after metacognition - retry if failed and under retry limit.
    """
    if state.get("metacog_passed", True):
        return "respond"

    retry_count = state.get("retry_count", 0)
    if retry_count < 2:
        logger.info(f"Metacog failed, retrying (attempt {retry_count + 1})")
        return "retry"

    logger.warning("Metacog failed but max retries reached, proceeding anyway")
    return "respond"


def finalize_response(state: GraphState) -> Dict[str, Any]:
    """
    Finalize the response with latency calculation.
    """
    start_time = state.get("start_time", time.perf_counter())
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "latency_ms": latency_ms,
    }


def build_workflow() -> StateGraph:
    """
    Build the cognitive workflow graph.

    Returns compiled StateGraph ready for .invoke() or .astream().
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("parse", parse_request)
    workflow.add_node("retrieve_memory", retrieve_memory)
    workflow.add_node("classify", classify_complexity)
    workflow.add_node("handle_status", handle_status)  # v16.3.3: Status node
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("call_model", call_model)
    workflow.add_node("store_memory", store_memory)
    workflow.add_node("metacog", metacog_verify)
    workflow.add_node("finalize", finalize_response)

    workflow.set_entry_point("parse")

    workflow.add_conditional_edges(
        "parse",
        should_use_memory,
        {
            "retrieve": "retrieve_memory",
            "skip": "classify",
        }
    )

    workflow.add_edge("retrieve_memory", "classify")

    # v16.3.3: Conditional routing after classify
    # Status queries short-circuit to handle_status, others go to knowledge
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "status": "handle_status",
            "knowledge": "retrieve_knowledge",
        }
    )

    # Status queries skip model call and go directly to store_memory
    workflow.add_edge("handle_status", "store_memory")

    workflow.add_edge("retrieve_knowledge", "call_model")

    workflow.add_edge("call_model", "store_memory")

    workflow.add_conditional_edges(
        "store_memory",
        should_run_metacog,
        {
            "verify": "metacog",
            "skip": "finalize",
        }
    )

    workflow.add_conditional_edges(
        "metacog",
        route_after_metacog,
        {
            "respond": "finalize",
            "retry": "call_model",
        }
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


cognitive_graph = build_workflow()


async def invoke_graph(
    prompt: str = "",
    messages: list = None,
    user_id: str = "default",
    chat_id: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
    model: str = "auto",
) -> Dict[str, Any]:
    """
    Invoke the cognitive graph with the given input.

    Args:
        model: Model override. Use "auto" for complexity-based routing,
               or specify "deepseek-v3.2", "qwen", etc. for manual override.

    Returns final state with response, usage, latency, etc.
    """
    initial_state: GraphState = {
        "prompt": prompt,
        "messages": messages or [],
        "user_id": user_id,
        "chat_id": chat_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
        "model": model,
    }

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("cognitive_graph") as span:
            span.set_attribute("prompt_length", len(prompt))
            span.set_attribute("user_id", user_id)

            final_state = await cognitive_graph.ainvoke(initial_state)

            span.set_attribute("complexity", str(final_state.get("complexity", "")))
            span.set_attribute("model", final_state.get("model_name", ""))
            span.set_attribute("latency_ms", final_state.get("latency_ms", 0))
            span.set_attribute("success", not final_state.get("error"))

            return final_state
    else:
        return await cognitive_graph.ainvoke(initial_state)


async def stream_graph(
    prompt: str = "",
    messages: list = None,
    user_id: str = "default",
    chat_id: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: str = "auto",
) -> AsyncIterator[str]:
    """
    Stream response from the cognitive graph.

    Runs classification, memory, and knowledge, then streams inference directly.
    Yields SSE-formatted chunks.
    """

    initial_state: GraphState = {
        "prompt": prompt,
        "messages": messages or [],
        "user_id": user_id,
        "chat_id": chat_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "model": model,
    }

    parsed = parse_request(initial_state)
    initial_state.update(parsed)

    if should_use_memory(initial_state) == "retrieve":
        memory_result = await retrieve_memory(initial_state)
        initial_state.update(memory_result)

    classify_result = classify_complexity(initial_state)
    initial_state.update(classify_result)

    # v16.3.3: Handle status queries without streaming (instant response)
    if initial_state.get("is_status_query", False):
        status_result = await handle_status(initial_state)
        response = status_result.get("response", "")
        yield f"data: {response}\n\n"
        yield "data: [DONE]\n\n"
        await store_memory(initial_state)
        return

    knowledge_result = await retrieve_knowledge(initial_state)
    initial_state.update(knowledge_result)

    async for line in stream_model_response(initial_state):
        yield line

    await store_memory(initial_state)


def get_graph_health() -> Dict[str, Any]:
    """
    Get health status of the cognitive graph.
    """
    return {
        "status": "ok",
        "graph_compiled": cognitive_graph is not None,
        "tracing_enabled": TRACING_ENABLED,
        "nodes": ["parse", "retrieve_memory", "classify", "handle_status",
                  "retrieve_knowledge", "call_model", "store_memory", "metacog", "finalize"],
    }
