"""
Classification Node (Phase 4.3 + v16.3.3 Operation Internalize)

Estimates task complexity using Sovereign Vocabulary and heuristics.
Detects status/introspection queries for short-circuit routing.
"""

import logging
from typing import Any, Dict

from .state import ComplexityLevel, ENDPOINTS, GraphState

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.graph.classification")
    TRACING_ENABLED = True
except ImportError:
    tracer = None
    TRACING_ENABLED = False

logger = logging.getLogger("omni.graph.classification")

# Sovereign Vocabulary (v15.2.1)
# Any prompt containing these keywords → COMPLEX routing
SOVEREIGN_VOCABULARY = [
    "ssh", "root", "kernel", "admin", "system", "deploy",
    "trace", "audit", "calculate", "math", "physics",
    "efficiency", "ratio", "power", "voltage", "watt",
    "gpu", "vram", "blackwell", "5090", "nvidia",
    "check", "monitor", "connect", "execute",
]

COMPLEX_INDICATORS = [
    "analyze", "design", "architect", "implement",
    "debug", "refactor", "optimize", "explain why",
    "compare", "evaluate", "plan", "strategy",
    "step by step", "reasoning", "prove",
]

TRIVIAL_INDICATORS = [
    "hello", "hi", "thanks", "thank you", "bye",
    "what time", "who are you", "help",
]

# Status/Introspection Keywords (v16.3.3 - Operation Internalize)
# Prompts containing these + asking about self → route to status node
STATUS_KEYWORDS = [
    "status report", "system status", "sovereign status",
    "how is your vram", "your vram", "your gpu",
    "how much vram", "vram usage", "gpu status",
    "memory status", "introspect", "self-check",
    "health report", "your health", "how are you doing",
]

# Valid model override aliases (v16.2.6)
# Maps user-facing model names to endpoint keys in ENDPOINTS
MODEL_ALIASES = {
    "deepseek-v3.2": "deepseek",
    "deepseek": "deepseek",
    "qwen2.5-coder-7b": "qwen",
    "qwen": "qwen",
    "qwen-executor": "qwen",
}


def classify_complexity(state: GraphState) -> Dict[str, Any]:
    """
    Classify task complexity based on prompt analysis.

    Supports manual model override via state["model"] parameter.

    Returns:
        State update with complexity and routing_reason
    """
    prompt = state.get("prompt", "")
    messages = state.get("messages", [])

    # Extract prompt from messages if not set
    if not prompt and messages:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break

    # v16.2.6: Check for explicit model override FIRST
    requested_model = state.get("model", "")
    if requested_model and requested_model.lower() != "auto":
        endpoint_key = MODEL_ALIASES.get(requested_model.lower())
        if endpoint_key and endpoint_key in ENDPOINTS:
            endpoint = ENDPOINTS[endpoint_key]
            reason = f"Manual override: {requested_model}"
            logger.info(f"Model override active: {endpoint.name}")

            if TRACING_ENABLED and tracer:
                with tracer.start_as_current_span("classify_complexity") as span:
                    span.set_attribute("override", True)
                    span.set_attribute("model", endpoint.name)
                    span.set_attribute("reason", reason)

            return {
                "complexity": ComplexityLevel.COMPLEX if endpoint_key == "deepseek" else ComplexityLevel.ROUTINE,
                "routing_reason": reason,
                "model_name": endpoint.name,
                "endpoint": endpoint.url,
                "prompt": prompt,
            }

    prompt_lower = prompt.lower()

    # v16.3.3: Check for status/introspection queries FIRST
    # These short-circuit to the status node instead of LLM
    for keyword in STATUS_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Status query detected: '{keyword}'")
            if TRACING_ENABLED and tracer:
                with tracer.start_as_current_span("classify_complexity") as span:
                    span.set_attribute("is_status_query", True)
                    span.set_attribute("status_keyword", keyword)
            return {
                "complexity": ComplexityLevel.TRIVIAL,
                "routing_reason": f"Status query: '{keyword}'",
                "is_status_query": True,
                "prompt": prompt,
            }

    def _classify() -> tuple[ComplexityLevel, str]:
        # Check for trivial indicators
        if any(ind in prompt_lower for ind in TRIVIAL_INDICATORS):
            if len(prompt) < 50:
                return ComplexityLevel.TRIVIAL, "Trivial greeting/command"

        # Check for tool orchestration requirement (from state)
        if state.get("requires_tool_orchestration"):
            return ComplexityLevel.TOOL_HEAVY, "Requires tool orchestration"

        # Sovereign Vocabulary check
        for keyword in SOVEREIGN_VOCABULARY:
            if keyword in prompt_lower:
                return ComplexityLevel.COMPLEX, f"Sovereign vocabulary: '{keyword}'"

        # Complex indicators check
        for indicator in COMPLEX_INDICATORS:
            if indicator in prompt_lower:
                return ComplexityLevel.COMPLEX, f"Complex indicator: '{indicator}'"

        # Length-based heuristics
        context_count = len(state.get("messages", [])) - 1  # Exclude current message
        if len(prompt) > 500 or context_count > 5:
            return ComplexityLevel.COMPLEX, f"Long prompt ({len(prompt)} chars) or deep context ({context_count} messages)"

        return ComplexityLevel.ROUTINE, "Default routine classification"

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("classify_complexity") as span:
            complexity, reason = _classify()
            span.set_attribute("complexity", complexity.value)
            span.set_attribute("reason", reason)
            span.set_attribute("prompt_length", len(prompt))
    else:
        complexity, reason = _classify()

    logger.info(f"Classified as {complexity.value}: {reason}")

    # Determine model and endpoint based on complexity
    if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.TOOL_HEAVY):
        model_name = "deepseek-v3.2"
        endpoint = "http://deepseek-v32:8000/v1"
    else:
        model_name = "qwen2.5-coder-7b"
        endpoint = "http://qwen-executor:8002/v1"

    return {
        "complexity": complexity,
        "routing_reason": reason,
        "model_name": model_name,
        "endpoint": endpoint,
        "prompt": prompt,  # Ensure prompt is set
    }
