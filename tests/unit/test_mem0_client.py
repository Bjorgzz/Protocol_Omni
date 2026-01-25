"""Unit tests for Mem0 client wrapper."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory.mem0_client import (
    Mem0Client,
    Memory,
    MemorySearchResult,
    format_memories_for_context,
)


@pytest.mark.unit
class TestMemory:
    """Test Memory dataclass."""

    def test_memory_creation(self):
        """Memory should be created with required fields."""
        memory = Memory(
            id="mem-123",
            content="User prefers dark mode",
            metadata={"source": "settings"},
            created_at=datetime.now(),
        )
        assert memory.id == "mem-123"
        assert memory.content == "User prefers dark mode"
        assert memory.metadata == {"source": "settings"}
        assert memory.score is None

    def test_memory_with_score(self):
        """Memory should support optional score."""
        memory = Memory(
            id="mem-456",
            content="Test content",
            metadata={},
            created_at=datetime.now(),
            score=0.95,
        )
        assert memory.score == 0.95


@pytest.mark.unit
class TestMemorySearchResult:
    """Test MemorySearchResult dataclass."""

    def test_search_result_creation(self):
        """Search result should contain memories and metadata."""
        memories = [
            Memory(id="1", content="Memory 1", metadata={}, created_at=datetime.now()),
            Memory(id="2", content="Memory 2", metadata={}, created_at=datetime.now()),
        ]
        result = MemorySearchResult(
            memories=memories,
            query="test query",
            total_count=2,
        )
        assert len(result.memories) == 2
        assert result.query == "test query"
        assert result.total_count == 2

    def test_empty_search_result(self):
        """Empty search result should be valid."""
        result = MemorySearchResult(
            memories=[],
            query="no results query",
            total_count=0,
        )
        assert len(result.memories) == 0
        assert result.total_count == 0


@pytest.mark.unit
class TestMem0Client:
    """Test Mem0Client class."""

    def test_client_initialization_default(self):
        """Client should use default URL."""
        client = Mem0Client()
        assert client.base_url == "http://localhost:8050"
        assert client.timeout == 30.0

    def test_client_initialization_custom(self):
        """Client should accept custom URL."""
        client = Mem0Client(base_url="http://mem0.example.com:9000", timeout=60.0)
        assert client.base_url == "http://mem0.example.com:9000"
        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Health check should return True on success."""
        client = Mem0Client()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.health_check()
            assert result is True
            mock_http.get.assert_called_once_with("/health")

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Health check should return False on failure."""
        client = Mem0Client()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get.side_effect = Exception("Connection refused")
            mock_get_client.return_value = mock_http

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        """Store memory should return memory ID on success."""
        client = Mem0Client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "mem-new-123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.store_memory(
                content="User likes Python",
                user_id="user-456",
                metadata={"source": "chat"},
            )

            assert result == "mem-new-123"

    @pytest.mark.asyncio
    async def test_store_memory_failure(self):
        """Store memory should return None on failure."""
        client = Mem0Client()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.side_effect = Exception("Server error")
            mock_get_client.return_value = mock_http

            result = await client.store_memory(
                content="Test content",
                user_id="user-789",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_search_memory_success(self):
        """Search memory should return results."""
        client = Mem0Client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "User prefers TypeScript",
                    "metadata": {},
                    "score": 0.92,
                },
                {
                    "id": "mem-2",
                    "memory": "User works on web apps",
                    "metadata": {},
                    "score": 0.85,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.search_memory(
                query="What languages does user prefer?",
                user_id="user-123",
                limit=5,
            )

            assert len(result.memories) == 2
            assert result.memories[0].content == "User prefers TypeScript"
            assert result.memories[0].score == 0.92

    @pytest.mark.asyncio
    async def test_search_memory_empty(self):
        """Search with no results should return empty list."""
        client = Mem0Client()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.side_effect = Exception("No results")
            mock_get_client.return_value = mock_http

            result = await client.search_memory(
                query="Nonexistent topic",
                user_id="user-999",
            )

            assert len(result.memories) == 0
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        """Delete memory should return True on success."""
        client = Mem0Client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_http.delete.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.delete_memory("mem-to-delete")
            assert result is True


@pytest.mark.unit
class TestFormatMemoriesForContext:
    """Test memory formatting for context injection."""

    def test_format_empty_memories(self):
        """Empty memory list should return empty string."""
        result = format_memories_for_context([])
        assert result == ""

    def test_format_single_memory(self):
        """Single memory should be formatted correctly."""
        memories = [
            Memory(id="1", content="User prefers dark mode", metadata={}, created_at=datetime.now())
        ]
        result = format_memories_for_context(memories)

        assert "<relevant_memories>" in result
        assert "</relevant_memories>" in result
        assert "User prefers dark mode" in result

    def test_format_multiple_memories(self):
        """Multiple memories should all be included."""
        memories = [
            Memory(id="1", content="Memory one", metadata={}, created_at=datetime.now()),
            Memory(id="2", content="Memory two", metadata={}, created_at=datetime.now()),
            Memory(id="3", content="Memory three", metadata={}, created_at=datetime.now()),
        ]
        result = format_memories_for_context(memories)

        assert "Memory one" in result
        assert "Memory two" in result
        assert "Memory three" in result

    def test_format_truncates_long_memories(self):
        """Long memories should be truncated."""
        memories = [
            Memory(id=str(i), content=f"Memory {i} " * 100, metadata={}, created_at=datetime.now())
            for i in range(50)
        ]
        result = format_memories_for_context(memories, max_tokens=100)

        assert "truncated" in result
