"""
Protocol OMNI Memory Module (Phase 4.2)

Persistent memory layer using Mem0 for context retention across sessions.
"""

from .mem0_client import Mem0Client, Memory, MemorySearchResult

__all__ = ["Mem0Client", "Memory", "MemorySearchResult"]
