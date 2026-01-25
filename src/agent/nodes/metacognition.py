"""
Metacognition Node (Phase 4.3)

4-gate verification node for response quality assurance.
Implements the metacognition protocol from Protocol OMNI v15.2.
"""

import logging
import os
import re
from typing import Any, Dict

from .state import ComplexityLevel, GraphState

logger = logging.getLogger("omni.agent.nodes.metacognition")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.agent.nodes.metacognition") if TRACING_ENABLED else None
except ImportError:
    tracer = None


GATE_1_HALLUCINATION_MARKERS = [
    r"as an ai",
    r"i cannot",
    r"i don't have access",
    r"i'm unable to",
    r"i apologize",
    r"i can't help",
    r"as a language model",
]

GATE_2_INCOMPLETE_MARKERS = [
    r"\.{3,}$",
    r"etc\.$",
    r"and so on\.$",
    r"to be continued",
    r"\[incomplete\]",
    r"\[truncated\]",
]

GATE_3_MIN_LENGTH = 50

MAX_RETRIES = 2


def should_verify(state: GraphState) -> bool:
    """
    Determine if metacognition verification should run.

    Only verifies COMPLEX and TOOL_HEAVY tasks.
    Skips TRIVIAL and ROUTINE to reduce latency.
    """
    complexity = state.get("complexity")

    if complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.ROUTINE):
        return False

    if state.get("error"):
        return False

    if not state.get("response"):
        return False

    return True


def metacog_verify(state: GraphState) -> Dict[str, Any]:
    """
    Run 4-gate verification on the model response.

    Gates:
    1. Hallucination Detection - Check for AI cop-out phrases
    2. Completeness Check - Look for truncation markers
    3. Length Validation - Ensure minimum substantive response
    4. Coherence Check - Verify response addresses the prompt

    Returns: State update with metacog_passed and metacog_verdict
    """
    if not should_verify(state):
        return {
            "metacog_passed": True,
            "metacog_verdict": "skipped",
        }

    response = state.get("response", "")
    prompt = state.get("prompt", "")
    retry_count = state.get("retry_count", 0)

    if TRACING_ENABLED and tracer:
        with tracer.start_as_current_span("metacog_verify") as span:
            span.set_attribute("response_length", len(response))
            span.set_attribute("retry_count", retry_count)
            result = _run_gates(response, prompt, retry_count, span)
            span.set_attribute("passed", result["metacog_passed"])
            span.set_attribute("verdict", result["metacog_verdict"])
            return result
    else:
        return _run_gates(response, prompt, retry_count, None)


def _run_gates(
    response: str,
    prompt: str,
    retry_count: int,
    span: Any
) -> Dict[str, Any]:
    """Run all verification gates."""

    gate_1_passed, gate_1_reason = _gate_1_hallucination(response)
    if not gate_1_passed:
        logger.warning(f"Gate 1 (Hallucination) failed: {gate_1_reason}")
        if span:
            span.set_attribute("failed_gate", 1)
        return _handle_failure("hallucination", gate_1_reason, retry_count)

    gate_2_passed, gate_2_reason = _gate_2_completeness(response)
    if not gate_2_passed:
        logger.warning(f"Gate 2 (Completeness) failed: {gate_2_reason}")
        if span:
            span.set_attribute("failed_gate", 2)
        return _handle_failure("incomplete", gate_2_reason, retry_count)

    gate_3_passed, gate_3_reason = _gate_3_length(response)
    if not gate_3_passed:
        logger.warning(f"Gate 3 (Length) failed: {gate_3_reason}")
        if span:
            span.set_attribute("failed_gate", 3)
        return _handle_failure("too_short", gate_3_reason, retry_count)

    gate_4_passed, gate_4_reason = _gate_4_coherence(response, prompt)
    if not gate_4_passed:
        logger.warning(f"Gate 4 (Coherence) failed: {gate_4_reason}")
        if span:
            span.set_attribute("failed_gate", 4)
        return _handle_failure("incoherent", gate_4_reason, retry_count)

    logger.info("Metacognition: All 4 gates passed")
    return {
        "metacog_passed": True,
        "metacog_verdict": "passed_all_gates",
    }


def _gate_1_hallucination(response: str) -> tuple[bool, str]:
    """
    Gate 1: Detect AI hallucination/cop-out phrases.

    These indicate the model is refusing or deflecting rather than answering.
    """
    response_lower = response.lower()

    for pattern in GATE_1_HALLUCINATION_MARKERS:
        if re.search(pattern, response_lower):
            return False, f"Detected hallucination marker: '{pattern}'"

    return True, "No hallucination markers detected"


def _gate_2_completeness(response: str) -> tuple[bool, str]:
    """
    Gate 2: Check for incomplete/truncated responses.

    Looks for trailing ellipses, "etc.", or explicit truncation markers.
    """
    response_stripped = response.strip()

    for pattern in GATE_2_INCOMPLETE_MARKERS:
        if re.search(pattern, response_stripped, re.IGNORECASE):
            return False, f"Detected incompleteness marker: '{pattern}'"

    if response_stripped and not re.match(r'[.!?`"\'\]\)>]$', response_stripped[-1]):
        if len(response_stripped) > 500:
            return False, "Long response ends without proper termination"

    return True, "Response appears complete"


def _gate_3_length(response: str) -> tuple[bool, str]:
    """
    Gate 3: Validate minimum response length.

    Very short responses for COMPLEX tasks indicate failure.
    """
    stripped = response.strip()

    if len(stripped) < GATE_3_MIN_LENGTH:
        return False, f"Response too short: {len(stripped)} chars (min: {GATE_3_MIN_LENGTH})"

    return True, f"Response length acceptable: {len(stripped)} chars"


def _gate_4_coherence(response: str, prompt: str) -> tuple[bool, str]:
    """
    Gate 4: Check if response addresses the prompt.

    Basic coherence check - does the response seem relevant?
    This is a lightweight heuristic, not full semantic analysis.
    """
    if not prompt or not response:
        return True, "No prompt or response to check"

    prompt_lower = prompt.lower()
    response_lower = response.lower()

    key_terms = _extract_key_terms(prompt_lower)

    if not key_terms:
        return True, "No key terms extracted from prompt"

    matching_terms = sum(1 for term in key_terms if term in response_lower)
    match_ratio = matching_terms / len(key_terms) if key_terms else 1.0

    if match_ratio < 0.2 and len(key_terms) >= 3:
        return False, f"Low term overlap ({match_ratio:.0%}): response may not address prompt"

    return True, f"Coherence check passed: {match_ratio:.0%} term overlap"


def _extract_key_terms(text: str) -> list[str]:
    """Extract key terms from text for coherence checking."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "must", "shall",
        "i", "you", "he", "she", "it", "we", "they", "me", "him",
        "her", "us", "them", "my", "your", "his", "its", "our",
        "their", "this", "that", "these", "those", "what", "which",
        "who", "whom", "whose", "when", "where", "why", "how",
        "and", "or", "but", "if", "then", "else", "for", "with",
        "to", "from", "in", "on", "at", "by", "of", "about",
        "please", "help", "want", "need", "like", "tell", "show",
    }

    words = re.findall(r'\b[a-z]{3,}\b', text)

    key_terms = [w for w in words if w not in stopwords]

    return list(set(key_terms))[:20]


def _handle_failure(
    failure_type: str,
    reason: str,
    retry_count: int
) -> Dict[str, Any]:
    """Handle verification failure - decide whether to retry or pass through."""

    if retry_count >= MAX_RETRIES:
        logger.warning(
            f"Metacognition: Max retries ({MAX_RETRIES}) reached, "
            f"passing through with warning"
        )
        return {
            "metacog_passed": True,
            "metacog_verdict": f"passed_after_max_retries:{failure_type}",
        }

    return {
        "metacog_passed": False,
        "metacog_verdict": f"failed:{failure_type}:{reason}",
        "retry_count": retry_count + 1,
    }


def get_retry_prompt_enhancement(failure_type: str) -> str:
    """
    Get prompt enhancement for retry based on failure type.

    Used when metacognition fails and we need to retry the model call.
    """
    enhancements = {
        "hallucination": (
            "Important: Provide a direct, substantive answer. "
            "Do not deflect or claim inability to help."
        ),
        "incomplete": (
            "Important: Provide a complete response. "
            "Do not truncate or leave the answer unfinished."
        ),
        "too_short": (
            "Important: Provide a thorough, detailed response. "
            "Brief answers are not sufficient for this query."
        ),
        "incoherent": (
            "Important: Focus on directly addressing the specific question asked. "
            "Ensure your response is relevant to the query."
        ),
    }

    return enhancements.get(failure_type, "")
