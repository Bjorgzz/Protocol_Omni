"""
Memgraph Client for Code Knowledge Graph
Protocol OMNI Phase 4.4 - SOVEREIGN COGNITION

Provides semantic code queries via Memgraph graph database.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("omni.knowledge.memgraph")

TRACING_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.knowledge.memgraph") if TRACING_ENABLED else None
except ImportError:
    tracer = None


@dataclass
class CodeSymbol:
    """Represents a code symbol (class, function, etc.)."""
    name: str
    qualified_name: str
    kind: str
    signature: str = ""
    docstring: str = ""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass
class CodeContext:
    """Aggregated code context for a query."""
    symbols: List[CodeSymbol] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""

    def to_prompt_context(self, max_chars: int = 2000) -> str:
        """Format code context for injection into prompt."""
        if not self.symbols:
            return ""

        lines = ["<code_knowledge_graph>"]

        for symbol in self.symbols[:10]:
            lines.append(f"- {symbol.kind}: {symbol.qualified_name}")
            if symbol.signature:
                lines.append(f"  Signature: {symbol.signature}")
            if symbol.docstring:
                lines.append(f"  Doc: {symbol.docstring[:200]}")
            if symbol.file_path:
                lines.append(f"  File: {symbol.file_path}:{symbol.line_start}")

        if self.relationships:
            lines.append("")
            lines.append("Relationships:")
            for rel in self.relationships[:5]:
                lines.append(f"  {rel.get('from')} --[{rel.get('type')}]--> {rel.get('to')}")

        lines.append("</code_knowledge_graph>")

        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars - 20] + "\n... (truncated)"

        return result


class MemgraphClient:
    """
    Client for querying Memgraph code knowledge graph.

    Connects to Memgraph via Bolt protocol and provides semantic
    code queries (find references, get dependencies, etc.).
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("MEMGRAPH_USER", "")
        self.password = password or os.getenv("MEMGRAPH_PASSWORD", "")
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of database driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password) if self.user else None
                )
            except ImportError:
                logger.error("neo4j driver not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Memgraph: {e}")
                raise
        return self._driver

    def close(self):
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def health_check(self) -> bool:
        """Check if Memgraph is accessible."""
        try:
            driver = self._get_driver()
            with driver.session() as session:
                result = session.run("RETURN 1 as n")
                return result.single()["n"] == 1
        except Exception as e:
            logger.warning(f"Memgraph health check failed: {e}")
            return False

    def find_symbol(self, name: str, kind: Optional[str] = None) -> List[CodeSymbol]:
        """
        Find symbols by name.

        Args:
            name: Symbol name to search (partial match)
            kind: Optional filter by kind (Class, Function)

        Returns:
            List of matching CodeSymbols
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("memgraph_find_symbol") as span:
                span.set_attribute("name", name)
                span.set_attribute("kind", kind or "any")
                return self._find_symbol_impl(name, kind)
        return self._find_symbol_impl(name, kind)

    def _find_symbol_impl(self, name: str, kind: Optional[str]) -> List[CodeSymbol]:
        """Internal implementation of find_symbol."""
        try:
            driver = self._get_driver()

            if kind:
                query = f"""
                MATCH (s:{kind})
                WHERE s.name CONTAINS $name
                OPTIONAL MATCH (f:File)-[:CONTAINS*]->(s)
                RETURN s, f.path as file_path
                LIMIT 20
                """
            else:
                query = """
                MATCH (s)
                WHERE (s:Class OR s:Function) AND s.name CONTAINS $name
                OPTIONAL MATCH (f:File)-[:CONTAINS*]->(s)
                RETURN s, labels(s)[0] as kind, f.path as file_path
                LIMIT 20
                """

            with driver.session() as session:
                result = session.run(query, name=name)
                symbols = []
                for record in result:
                    s = record["s"]
                    symbol_kind = kind or record.get("kind", "Symbol")
                    symbols.append(CodeSymbol(
                        name=s.get("name", ""),
                        qualified_name=s.get("qualified_name", ""),
                        kind=symbol_kind,
                        signature=s.get("signature", ""),
                        docstring=s.get("docstring", ""),
                        file_path=record.get("file_path", ""),
                        line_start=s.get("line_start", 0),
                        line_end=s.get("line_end", 0),
                    ))
                return symbols

        except Exception as e:
            logger.error(f"find_symbol failed: {e}")
            return []

    def find_references(self, symbol_name: str) -> List[CodeSymbol]:
        """
        Find all references (callers) of a symbol.

        Args:
            symbol_name: Name of the symbol to find references for

        Returns:
            List of symbols that reference the target
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("memgraph_find_references") as span:
                span.set_attribute("symbol_name", symbol_name)
                return self._find_references_impl(symbol_name)
        return self._find_references_impl(symbol_name)

    def _find_references_impl(self, symbol_name: str) -> List[CodeSymbol]:
        """Internal implementation of find_references."""
        try:
            driver = self._get_driver()

            query = """
            MATCH (caller:Function)-[:CALLS]->(target:Function)
            WHERE target.name = $name
            OPTIONAL MATCH (f:File)-[:CONTAINS*]->(caller)
            RETURN caller, f.path as file_path
            LIMIT 20
            """

            with driver.session() as session:
                result = session.run(query, name=symbol_name)
                symbols = []
                for record in result:
                    s = record["caller"]
                    symbols.append(CodeSymbol(
                        name=s.get("name", ""),
                        qualified_name=s.get("qualified_name", ""),
                        kind="Function",
                        signature=s.get("signature", ""),
                        docstring=s.get("docstring", ""),
                        file_path=record.get("file_path", ""),
                        line_start=s.get("line_start", 0),
                        line_end=s.get("line_end", 0),
                    ))
                return symbols

        except Exception as e:
            logger.error(f"find_references failed: {e}")
            return []

    def get_file_symbols(self, file_path: str) -> List[CodeSymbol]:
        """
        Get all symbols defined in a file.

        Args:
            file_path: Path to the file

        Returns:
            List of symbols in the file
        """
        try:
            driver = self._get_driver()

            query = """
            MATCH (f:File {path: $path})-[:CONTAINS]->(s)
            RETURN s, labels(s)[0] as kind
            UNION
            MATCH (f:File {path: $path})-[:CONTAINS]->(c:Class)-[:CONTAINS]->(s:Function)
            RETURN s, 'Method' as kind
            """

            with driver.session() as session:
                result = session.run(query, path=file_path)
                symbols = []
                for record in result:
                    s = record["s"]
                    symbols.append(CodeSymbol(
                        name=s.get("name", ""),
                        qualified_name=s.get("qualified_name", ""),
                        kind=record.get("kind", "Symbol"),
                        signature=s.get("signature", ""),
                        docstring=s.get("docstring", ""),
                        file_path=file_path,
                        line_start=s.get("line_start", 0),
                        line_end=s.get("line_end", 0),
                    ))
                return symbols

        except Exception as e:
            logger.error(f"get_file_symbols failed: {e}")
            return []

    def get_dependencies(self, file_path: str) -> List[str]:
        """
        Get all imports/dependencies of a file.

        Args:
            file_path: Path to the file

        Returns:
            List of module names imported by the file
        """
        try:
            driver = self._get_driver()

            query = """
            MATCH (f:File {path: $path})-[:IMPORTS]->(i:Import)
            RETURN i.module as module
            """

            with driver.session() as session:
                result = session.run(query, path=file_path)
                return [record["module"] for record in result]

        except Exception as e:
            logger.error(f"get_dependencies failed: {e}")
            return []

    def get_class_hierarchy(self, class_name: str) -> List[Dict[str, Any]]:
        """
        Get inheritance hierarchy for a class.

        Args:
            class_name: Name of the class

        Returns:
            List of inheritance relationships
        """
        try:
            driver = self._get_driver()

            query = """
            MATCH path = (child:Class)-[:INHERITS*]->(ancestor:Class)
            WHERE child.name = $name
            UNWIND relationships(path) as rel
            WITH startNode(rel) as child, endNode(rel) as parent
            RETURN child.name as child, parent.name as parent
            """

            with driver.session() as session:
                result = session.run(query, name=class_name)
                return [
                    {"child": r["child"], "parent": r["parent"]}
                    for r in result
                ]

        except Exception as e:
            logger.error(f"get_class_hierarchy failed: {e}")
            return []

    def get_code_context(
        self,
        query: str,
        limit: int = 10,
    ) -> CodeContext:
        """
        Get aggregated code context for a natural language query.

        Extracts likely symbol names from query and searches graph.

        Args:
            query: Natural language query about code
            limit: Maximum symbols to return

        Returns:
            CodeContext with relevant symbols
        """
        if TRACING_ENABLED and tracer:
            with tracer.start_as_current_span("memgraph_get_code_context") as span:
                span.set_attribute("query", query[:100])
                return self._get_code_context_impl(query, limit)
        return self._get_code_context_impl(query, limit)

    def _get_code_context_impl(self, query: str, limit: int) -> CodeContext:
        """Internal implementation of get_code_context."""
        import re

        potential_names = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*|[a-z_][a-z0-9_]+)\b', query)

        keywords_to_skip = {
            "the", "this", "that", "what", "where", "when", "how", "why",
            "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might",
            "can", "find", "get", "set", "all", "any", "some",
            "function", "class", "method", "file", "code", "implement",
        }

        search_terms = [
            name for name in potential_names
            if name.lower() not in keywords_to_skip and len(name) > 2
        ]

        all_symbols = []
        for term in search_terms[:5]:
            symbols = self.find_symbol(term)
            all_symbols.extend(symbols)

        seen = set()
        unique_symbols = []
        for s in all_symbols:
            if s.qualified_name not in seen:
                seen.add(s.qualified_name)
                unique_symbols.append(s)

        return CodeContext(
            symbols=unique_symbols[:limit],
            relationships=[],
            query=query,
        )
