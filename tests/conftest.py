"""Protocol OMNI v16.2 Test Configuration."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (require services)")
    config.addinivalue_line("markers", "remote: Remote host tests (require SSH access)")


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--run-remote",
        action="store_true",
        default=False,
        help="Run tests requiring remote SSH access",
    )


def pytest_collection_modifyitems(config, items):
    """Skip remote tests unless --run-remote is specified."""
    if config.getoption("--run-remote"):
        return
    skip_remote = pytest.mark.skip(reason="need --run-remote option to run")
    for item in items:
        if "remote" in item.keywords:
            item.add_marker(skip_remote)


@pytest.fixture
def sample_prompt() -> str:
    """Sample user prompt for testing."""
    return "Explain how LangGraph handles state management in cognitive workflows."


@pytest.fixture
def sample_messages() -> list:
    """Sample message history for testing."""
    return [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "What is Protocol OMNI?"},
        {"role": "assistant", "content": "Protocol OMNI is a sovereign cognition framework."},
        {"role": "user", "content": "How does the memory system work?"},
    ]


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Mock LLM response for testing."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "This is a test response from the LLM.",
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
        "model": "deepseek-v3.2",
    }


@pytest.fixture
def mock_mem0_client():
    """Mock Mem0 AsyncMemory client for testing."""
    mock = AsyncMock()
    mock.add.return_value = {
        "id": "mem-test-12345",
        "status": "created",
        "message": "Memory stored successfully",
    }
    mock.search.return_value = {
        "results": [
            {
                "id": "mem-001",
                "memory": "User prefers concise explanations",
                "score": 0.92,
            },
            {
                "id": "mem-002",
                "memory": "User works on AI systems",
                "score": 0.87,
            },
        ]
    }
    mock.get_all.return_value = [
        {"id": "mem-001", "memory": "User prefers concise explanations"},
        {"id": "mem-002", "memory": "User works on AI systems"},
    ]
    mock.delete.return_value = {"status": "deleted"}
    return mock


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for vector store testing."""
    mock = MagicMock()
    mock.get_collections.return_value.collections = [
        MagicMock(name="mem0"),
        MagicMock(name="mem0_memories"),
    ]
    mock.search.return_value = [
        MagicMock(id="point-1", score=0.95, payload={"content": "Test memory"}),
    ]
    return mock


@pytest.fixture
def graph_state() -> Dict[str, Any]:
    """Sample graph state for workflow testing."""
    return {
        "prompt": "Explain cognitive routing in AI systems",
        "messages": [],
        "user_id": "test-user",
        "chat_id": "test-chat-001",
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": False,
        "complexity": None,
        "model_name": None,
        "response": None,
        "latency_ms": 0,
    }
