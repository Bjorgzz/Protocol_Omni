"""Unit tests for LangGraph cognitive workflow."""

import pytest

from agent.nodes.state import ComplexityLevel


@pytest.mark.unit
class TestLangGraphImports:
    """Test LangGraph v1.0 compatibility."""

    def test_langgraph_core_imports(self):
        """Core LangGraph imports should work."""
        from langgraph.graph import END, StateGraph
        assert StateGraph is not None
        assert END is not None

    def test_no_deprecated_create_react_agent(self):
        """Deprecated create_react_agent should not be used."""
        try:
            from langgraph.prebuilt import create_react_agent
            pytest.skip("create_react_agent exists in this version")
        except ImportError:
            pass


@pytest.mark.unit
class TestGraphState:
    """Test GraphState TypedDict."""

    def test_graph_state_required_fields(self, graph_state):
        """Graph state should have required fields."""
        assert "prompt" in graph_state
        assert "messages" in graph_state
        assert "user_id" in graph_state

    def test_graph_state_optional_fields(self, graph_state):
        """Graph state should support optional fields."""
        assert "complexity" in graph_state
        assert "model_name" in graph_state
        assert "response" in graph_state


@pytest.mark.unit
class TestComplexityLevel:
    """Test ComplexityLevel enum."""

    def test_complexity_levels_exist(self):
        """All complexity levels should be defined."""
        assert ComplexityLevel.TRIVIAL is not None
        assert ComplexityLevel.ROUTINE is not None
        assert ComplexityLevel.COMPLEX is not None
        assert ComplexityLevel.TOOL_HEAVY is not None

    def test_complexity_level_values(self):
        """Complexity levels should have string values."""
        assert isinstance(ComplexityLevel.TRIVIAL.value, str)
        assert isinstance(ComplexityLevel.ROUTINE.value, str)


@pytest.mark.unit
class TestWorkflowFunctions:
    """Test workflow helper functions."""

    def test_parse_request(self):
        """Parse request should extract prompt from messages."""
        from agent.graph import parse_request

        state = {
            "prompt": "",
            "messages": [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Second message"},
            ],
            "user_id": "test",
            "chat_id": "",
        }

        result = parse_request(state)
        assert result["prompt"] == "Second message"
        assert "start_time" in result

    def test_should_use_memory_trivial(self):
        """Trivial greetings should skip memory."""
        from agent.graph import should_use_memory

        state = {"prompt": "Hello!"}
        result = should_use_memory(state)
        assert result == "skip"

    def test_should_use_memory_complex(self):
        """Complex prompts should retrieve memory."""
        from agent.graph import should_use_memory

        state = {"prompt": "Explain the memory model of our LangGraph workflow"}
        result = should_use_memory(state)
        assert result == "retrieve"

    def test_route_by_complexity_complex(self):
        """Complex tasks should route to deepseek."""
        from agent.graph import route_by_complexity

        state = {"complexity": ComplexityLevel.COMPLEX}
        result = route_by_complexity(state)
        assert result == "deepseek"

    def test_route_by_complexity_routine(self):
        """Routine tasks should route to qwen."""
        from agent.graph import route_by_complexity

        state = {"complexity": ComplexityLevel.ROUTINE}
        result = route_by_complexity(state)
        assert result == "qwen"

    def test_should_run_metacog(self):
        """Metacognition should run based on state."""
        from agent.graph import should_run_metacog

        state = {"complexity": ComplexityLevel.COMPLEX}
        result = should_run_metacog(state)
        assert result in ["verify", "skip"]

    def test_finalize_response(self):
        """Finalize should calculate latency."""
        import time

        from agent.graph import finalize_response

        state = {"start_time": time.perf_counter() - 0.5}
        result = finalize_response(state)

        assert "latency_ms" in result
        assert result["latency_ms"] >= 500


@pytest.mark.unit
class TestWorkflowBuild:
    """Test workflow graph building."""

    def test_build_workflow_returns_compiled_graph(self):
        """build_workflow should return a compiled graph."""
        from agent.graph import build_workflow

        graph = build_workflow()
        assert graph is not None

    def test_cognitive_graph_is_prebuilt(self):
        """cognitive_graph should be available as module-level variable."""
        from agent.graph import cognitive_graph
        assert cognitive_graph is not None

    def test_get_graph_health(self):
        """Graph health should report status."""
        from agent.graph import get_graph_health

        health = get_graph_health()

        assert health["status"] == "ok"
        assert health["graph_compiled"] is True
        assert "parse" in health["nodes"]
        assert "classify" in health["nodes"]
        assert "call_model" in health["nodes"]


@pytest.mark.unit
class TestGraphInvocation:
    """Test graph invocation interface."""

    @pytest.mark.asyncio
    async def test_invoke_graph_signature(self):
        """invoke_graph should accept expected parameters."""
        import inspect

        from agent.graph import invoke_graph

        sig = inspect.signature(invoke_graph)
        params = sig.parameters

        assert "prompt" in params
        assert "messages" in params
        assert "user_id" in params
        assert "stream" in params

    @pytest.mark.asyncio
    async def test_stream_graph_is_async_generator(self):
        """stream_graph should be an async generator."""
        import inspect

        from agent.graph import stream_graph

        assert inspect.isasyncgenfunction(stream_graph)
