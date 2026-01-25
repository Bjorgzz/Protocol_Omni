"""
Graph State Definition (Phase 4.3)

Defines the state schema that flows through the LangGraph workflow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class ComplexityLevel(str, Enum):
    """Task complexity levels for cognitive routing."""
    TRIVIAL = "trivial"
    ROUTINE = "routine"
    COMPLEX = "complex"
    TOOL_HEAVY = "tool_heavy"


class GraphState(TypedDict, total=False):
    """
    State that flows through the cognitive graph.

    Each node receives this state and returns partial updates.
    """
    # Input
    prompt: str
    messages: List[Dict[str, Any]]
    user_id: str
    chat_id: str
    temperature: float
    max_tokens: int
    stream: bool
    model: str  # v16.2.6: Manual model override (default "auto")

    # Routing
    complexity: ComplexityLevel
    routing_reason: str
    model_name: str
    endpoint: str
    is_status_query: bool  # v16.3.3: Flag for status/introspection queries

    # Memory
    memories: List[Dict[str, Any]]
    memory_context: str

    # Knowledge Graph
    code_context: str

    # Response
    response: str
    usage: Dict[str, int]
    raw_status: Dict[str, Any]  # v16.3.3: Raw status data from introspection

    # Metacognition
    metacog_verdict: str
    metacog_passed: bool
    retry_count: int

    # Metadata
    start_time: float
    latency_ms: float
    error: Optional[str]


@dataclass
class ModelEndpoint:
    """Model endpoint configuration."""
    name: str
    url: str
    model_id: str
    timeout: float = 300.0


# Model endpoint configurations
ENDPOINTS = {
    "deepseek": ModelEndpoint(
        name="deepseek-v3.2",
        url="http://deepseek-v32:8000/v1",
        model_id="deepseek-v3.2",
        timeout=300.0,
    ),
    "qwen": ModelEndpoint(
        name="qwen-executor",
        url="http://qwen-executor:8002/v1",
        model_id="qwen2.5-coder-7b",
        timeout=60.0,
    ),
}
