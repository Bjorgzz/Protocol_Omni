"""Unit tests for complexity classification node."""

import pytest

from agent.nodes.classification import (
    COMPLEX_INDICATORS,
    SOVEREIGN_VOCABULARY,
    TRIVIAL_INDICATORS,
    classify_complexity,
)
from agent.nodes.state import ComplexityLevel


@pytest.mark.unit
class TestClassifyComplexity:
    """Test complexity classification logic."""

    def test_trivial_greeting_short(self):
        """Short greetings should be classified as TRIVIAL."""
        state = {"prompt": "Hello!", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.TRIVIAL
        assert "Trivial" in result["routing_reason"]

    def test_trivial_greeting_thanks(self):
        """Thanks should be TRIVIAL."""
        state = {"prompt": "Thank you", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.TRIVIAL

    def test_sovereign_vocabulary_ssh(self):
        """Sovereign vocabulary 'ssh' should trigger COMPLEX."""
        state = {"prompt": "Connect via SSH to the server", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX
        assert "Sovereign vocabulary" in result["routing_reason"]
        assert "ssh" in result["routing_reason"]

    def test_sovereign_vocabulary_gpu(self):
        """GPU-related queries should be COMPLEX."""
        state = {"prompt": "Check GPU memory usage", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX

    def test_complex_indicator_analyze(self):
        """Complex indicators like 'analyze' should trigger COMPLEX."""
        state = {"prompt": "Analyze the performance metrics", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX
        assert "Complex indicator" in result["routing_reason"]

    def test_complex_indicator_step_by_step(self):
        """Step-by-step requests should be COMPLEX."""
        state = {"prompt": "Walk me through step by step the process", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX

    def test_routine_simple_question(self):
        """Simple questions without indicators should be ROUTINE."""
        state = {"prompt": "What is a variable?", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.ROUTINE
        assert "Default routine" in result["routing_reason"]

    def test_tool_orchestration_override(self):
        """Tool orchestration flag should force TOOL_HEAVY."""
        state = {
            "prompt": "Simple question",
            "messages": [],
            "requires_tool_orchestration": True,
        }
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.TOOL_HEAVY

    def test_long_prompt_complex(self):
        """Long prompts (>500 chars) should be COMPLEX."""
        long_prompt = "Please help me with " + "a" * 500
        state = {"prompt": long_prompt, "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX
        assert "Long prompt" in result["routing_reason"]

    def test_deep_context_complex(self):
        """Deep conversation context (>5 messages) should be COMPLEX."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(7)]
        state = {"prompt": "Continue", "messages": messages}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX

    def test_model_routing_complex(self):
        """COMPLEX tasks should route to deepseek-v3.2."""
        state = {"prompt": "Analyze the memory layout of the system", "messages": []}
        result = classify_complexity(state)
        assert result["model_name"] == "deepseek-v3.2"
        assert "deepseek-v32" in result["endpoint"]

    def test_model_routing_routine(self):
        """ROUTINE tasks should route to qwen."""
        state = {"prompt": "What is Python?", "messages": []}
        result = classify_complexity(state)
        assert result["model_name"] == "qwen2.5-coder-7b"
        assert "qwen-executor" in result["endpoint"]

    def test_extract_prompt_from_messages(self):
        """Prompt should be extracted from messages if not set."""
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "Answer"},
            {"role": "user", "content": "Analyze the data model for errors"},
        ]
        state = {"prompt": "", "messages": messages}
        result = classify_complexity(state)
        assert result["prompt"] == "Analyze the data model for errors"
        assert result["complexity"] == ComplexityLevel.COMPLEX

    def test_case_insensitive_matching(self):
        """Keywords should match case-insensitively."""
        state = {"prompt": "SSH connection to SERVER", "messages": []}
        result = classify_complexity(state)
        assert result["complexity"] == ComplexityLevel.COMPLEX


@pytest.mark.unit
class TestVocabularyLists:
    """Test vocabulary lists are properly defined."""

    def test_sovereign_vocabulary_not_empty(self):
        """Sovereign vocabulary should contain keywords."""
        assert len(SOVEREIGN_VOCABULARY) > 0
        assert "ssh" in SOVEREIGN_VOCABULARY
        assert "gpu" in SOVEREIGN_VOCABULARY

    def test_complex_indicators_not_empty(self):
        """Complex indicators should contain patterns."""
        assert len(COMPLEX_INDICATORS) > 0
        assert "analyze" in COMPLEX_INDICATORS

    def test_trivial_indicators_not_empty(self):
        """Trivial indicators should contain greetings."""
        assert len(TRIVIAL_INDICATORS) > 0
        assert "hello" in TRIVIAL_INDICATORS
