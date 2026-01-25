"""
Protocol OMNI Knowledge Module (Phase 4.4)

Memgraph-based code knowledge graph for semantic code queries.
"""

from .memgraph_client import CodeContext, CodeSymbol, MemgraphClient

__all__ = ["MemgraphClient", "CodeSymbol", "CodeContext"]
