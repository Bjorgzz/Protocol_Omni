"""
Mem0 Client Wrapper (Phase 4.2)

Production-grade persistent memory for cognitive routing.
Replaces passive Letta with 26% better accuracy, 91% faster retrieval.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

# OTEL instrumentation for Phoenix traces
try:
    from opentelemetry import trace
    TRACING_ENABLED = True
    tracer = trace.get_tracer("omni.memory")
except ImportError:
    TRACING_ENABLED = False
    tracer = None


@dataclass
class Memory:
    """A single memory record."""
    id: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    score: Optional[float] = None


@dataclass
class MemorySearchResult:
    """Results from a memory search."""
    memories: List[Memory]
    query: str
    total_count: int


class Mem0Client:
    """
    Client wrapper for Mem0 memory service.

    Usage:
        client = Mem0Client()

        # Store a memory
        memory_id = await client.store_memory(
            content="User prefers TypeScript over JavaScript",
            user_id="user-123",
            metadata={"source": "conversation", "topic": "preferences"}
        )

        # Retrieve relevant memories
        results = await client.search_memory(
            query="What languages does the user prefer?",
            user_id="user-123",
            limit=5
        )
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize Mem0 client.

        Args:
            base_url: Mem0 server URL. Defaults to MEM0_URL env var or http://localhost:8050.
                      Note: For internal Docker network, use http://mem0:8000 (container port).
                      For host/external access, use http://localhost:8050 (mapped port).
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("MEM0_URL", "http://localhost:8050")
        self.timeout = timeout
        self.logger = logging.getLogger("omni.memory.mem0")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Check if Mem0 service is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Mem0 health check failed: {e}")
            return False

    async def store_memory(
        self,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Store a memory in Mem0.

        Args:
            content: The memory content to store
            user_id: User identifier for memory scoping
            metadata: Optional metadata (source, topic, etc.)
            agent_id: Optional agent identifier

        Returns:
            Memory ID if successful, None otherwise
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("mem0_store") as span:
                span.set_attribute("user_id", user_id)
                span.set_attribute("content_length", len(content))
                return await self._store_memory_impl(content, user_id, metadata, agent_id, span)
        else:
            return await self._store_memory_impl(content, user_id, metadata, agent_id, None)

    async def _store_memory_impl(
        self,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]],
        agent_id: Optional[str],
        span: Any,
    ) -> Optional[str]:
        """Internal implementation of store_memory."""
        try:
            client = await self._get_client()

            payload = {
                "messages": [{"role": "user", "content": content}],
                "user_id": user_id,
            }
            if metadata:
                payload["metadata"] = metadata
            if agent_id:
                payload["agent_id"] = agent_id

            response = await client.post("/v1/memories/", json=payload)
            response.raise_for_status()

            data = response.json()
            memory_id = data.get("id") or data.get("memory_id")

            if span:
                span.set_attribute("memory_id", memory_id or "unknown")
                span.set_attribute("success", True)

            self.logger.debug(f"Stored memory {memory_id} for user {user_id}")
            return memory_id

        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            if span:
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)
            return None

    async def search_memory(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        agent_id: Optional[str] = None,
    ) -> MemorySearchResult:
        """
        Search for relevant memories.

        Args:
            query: Search query
            user_id: User identifier for memory scoping
            limit: Maximum number of results
            agent_id: Optional agent identifier

        Returns:
            MemorySearchResult with matching memories
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("mem0_search") as span:
                span.set_attribute("user_id", user_id)
                span.set_attribute("query_length", len(query))
                span.set_attribute("limit", limit)
                return await self._search_memory_impl(query, user_id, limit, agent_id, span)
        else:
            return await self._search_memory_impl(query, user_id, limit, agent_id, None)

    async def _search_memory_impl(
        self,
        query: str,
        user_id: str,
        limit: int,
        agent_id: Optional[str],
        span: Any,
    ) -> MemorySearchResult:
        """Internal implementation of search_memory."""
        try:
            client = await self._get_client()

            payload = {
                "query": query,
                "user_id": user_id,
                "limit": limit,
            }
            if agent_id:
                payload["agent_id"] = agent_id

            response = await client.post("/v1/memories/search/", json=payload)
            response.raise_for_status()

            data = response.json()
            memories_data = data.get("results", data.get("memories", []))

            memories = []
            for m in memories_data:
                memories.append(Memory(
                    id=m.get("id", ""),
                    content=m.get("memory", m.get("content", "")),
                    metadata=m.get("metadata", {}),
                    created_at=datetime.fromisoformat(m["created_at"]) if m.get("created_at") else datetime.now(),
                    updated_at=datetime.fromisoformat(m["updated_at"]) if m.get("updated_at") else None,
                    score=m.get("score"),
                ))

            result = MemorySearchResult(
                memories=memories,
                query=query,
                total_count=len(memories),
            )

            if span:
                span.set_attribute("results_count", len(memories))
                span.set_attribute("success", True)

            self.logger.debug(f"Found {len(memories)} memories for query: {query[:50]}...")
            return result

        except Exception as e:
            self.logger.error(f"Failed to search memories: {e}")
            if span:
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)
            return MemorySearchResult(memories=[], query=query, total_count=0)

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            Memory if found, None otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/v1/memories/{memory_id}/")
            response.raise_for_status()

            m = response.json()
            return Memory(
                id=m.get("id", memory_id),
                content=m.get("memory", m.get("content", "")),
                metadata=m.get("metadata", {}),
                created_at=datetime.fromisoformat(m["created_at"]) if m.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(m["updated_at"]) if m.get("updated_at") else None,
            )
        except Exception as e:
            self.logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.

        Args:
            memory_id: The memory ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.delete(f"/v1/memories/{memory_id}/")
            response.raise_for_status()
            self.logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def get_all_memories(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[Memory]:
        """
        Get all memories for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of memories to return

        Returns:
            List of memories
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/v1/memories/",
                params={"user_id": user_id, "limit": limit}
            )
            response.raise_for_status()

            data = response.json()
            memories_data = data.get("results", data.get("memories", []))

            return [
                Memory(
                    id=m.get("id", ""),
                    content=m.get("memory", m.get("content", "")),
                    metadata=m.get("metadata", {}),
                    created_at=datetime.fromisoformat(m["created_at"]) if m.get("created_at") else datetime.now(),
                    updated_at=datetime.fromisoformat(m["updated_at"]) if m.get("updated_at") else None,
                )
                for m in memories_data
            ]
        except Exception as e:
            self.logger.error(f"Failed to get memories for user {user_id}: {e}")
            return []


def format_memories_for_context(memories: List[Memory], max_tokens: int = 1000) -> str:
    """
    Format memories for injection into prompt context.

    Args:
        memories: List of memories to format
        max_tokens: Approximate max tokens (rough estimate)

    Returns:
        Formatted string for context injection
    """
    if not memories:
        return ""

    lines = ["<relevant_memories>"]
    char_count = 0
    max_chars = max_tokens * 4  # Rough token-to-char estimate

    for memory in memories:
        line = f"- {memory.content}"
        if char_count + len(line) > max_chars:
            lines.append("- ... (additional memories truncated)")
            break
        lines.append(line)
        char_count += len(line)

    lines.append("</relevant_memories>")
    return "\n".join(lines)
