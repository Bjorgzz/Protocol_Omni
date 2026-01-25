#!/usr/bin/env python3
"""
Code Indexer for Memgraph Knowledge Graph
Protocol OMNI Phase 4.4 - SOVEREIGN COGNITION

Parses Python source files using AST and indexes symbols + relationships
into Memgraph for semantic code queries.

Usage:
    python scripts/index_code.py src/
    python scripts/index_code.py src/agent/router.py
"""

import ast
import os
import sys
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase
    DRIVER_AVAILABLE = True
except ImportError:
    logger.warning("neo4j driver not installed, will generate Cypher only")
    DRIVER_AVAILABLE = False


@dataclass
class FunctionDef:
    """Represents a function or method definition."""
    name: str
    qualified_name: str
    signature: str
    docstring: str
    line_start: int
    line_end: int
    is_async: bool
    is_method: bool
    calls: List[str] = field(default_factory=list)


@dataclass
class ClassDef:
    """Represents a class definition."""
    name: str
    qualified_name: str
    docstring: str
    line_start: int
    line_end: int
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionDef] = field(default_factory=list)


@dataclass
class ImportDef:
    """Represents an import statement."""
    module: str
    qualified_name: str
    alias: Optional[str] = None


@dataclass
class FileDef:
    """Represents a Python file."""
    path: str
    name: str
    language: str
    lines: int
    classes: List[ClassDef] = field(default_factory=list)
    functions: List[FunctionDef] = field(default_factory=list)
    imports: List[ImportDef] = field(default_factory=list)


class CodeVisitor(ast.NodeVisitor):
    """AST visitor that extracts code symbols and relationships."""
    
    def __init__(self, module_prefix: str):
        self.module_prefix = module_prefix
        self.classes: List[ClassDef] = []
        self.functions: List[FunctionDef] = []
        self.imports: List[ImportDef] = []
        self._current_class: Optional[str] = None
        self._function_calls: Set[str] = set()
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportDef(
                module=alias.name,
                qualified_name=alias.name,
                alias=alias.asname,
            ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(ImportDef(
                module=module,
                qualified_name=full_name,
                alias=alias.asname,
            ))
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        qualified_name = f"{self.module_prefix}.{node.name}"
        
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))
        
        docstring = ast.get_docstring(node) or ""
        if docstring:
            docstring = docstring.split("\n\n")[0][:500]
        
        class_def = ClassDef(
            name=node.name,
            qualified_name=qualified_name,
            docstring=docstring,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            methods=[],
        )
        
        old_class = self._current_class
        self._current_class = qualified_name
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._extract_function(item, is_method=True)
                class_def.methods.append(method)
        
        self._current_class = old_class
        self.classes.append(class_def)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self._current_class is None:
            func = self._extract_function(node, is_method=False)
            self.functions.append(func)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if self._current_class is None:
            func = self._extract_function(node, is_method=False)
            self.functions.append(func)
    
    def _extract_function(self, node, is_method: bool) -> FunctionDef:
        """Extract function definition from AST node."""
        if self._current_class:
            qualified_name = f"{self._current_class}.{node.name}"
        else:
            qualified_name = f"{self.module_prefix}.{node.name}"
        
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"
        
        is_async = isinstance(node, ast.AsyncFunctionDef)
        prefix = "async def" if is_async else "def"
        signature = f"{prefix} {node.name}({', '.join(args)}){returns}"
        
        docstring = ast.get_docstring(node) or ""
        if docstring:
            docstring = docstring.split("\n\n")[0][:500]
        
        calls = self._find_calls(node)
        
        return FunctionDef(
            name=node.name,
            qualified_name=qualified_name,
            signature=signature,
            docstring=docstring,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_async=is_async,
            is_method=is_method,
            calls=calls,
        )
    
    def _find_calls(self, node) -> List[str]:
        """Find all function calls within a node."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))


def parse_file(file_path: Path, base_path: Path) -> Optional[FileDef]:
    """Parse a Python file and extract symbols."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return None
    
    relative_path = file_path.relative_to(base_path)
    module_prefix = str(relative_path.with_suffix("")).replace(os.sep, ".")
    
    visitor = CodeVisitor(module_prefix)
    visitor.visit(tree)
    
    line_count = len(content.splitlines())
    
    return FileDef(
        path=str(file_path.absolute()),
        name=file_path.name,
        language="python",
        lines=line_count,
        classes=visitor.classes,
        functions=visitor.functions,
        imports=visitor.imports,
    )


def generate_cypher(files: List[FileDef]) -> str:
    """Generate Cypher statements for indexing."""
    statements = []
    
    for f in files:
        statements.append(
            f"MERGE (file:File {{path: '{f.path}'}}) "
            f"SET file.name = '{f.name}', "
            f"file.language = '{f.language}', "
            f"file.lines = {f.lines}, "
            f"file.indexed_at = datetime();"
        )
        
        for imp in f.imports:
            safe_module = imp.module.replace("'", "\\'")
            safe_qname = imp.qualified_name.replace("'", "\\'")
            statements.append(
                f"MERGE (imp:Import {{qualified_name: '{safe_qname}'}}) "
                f"SET imp.module = '{safe_module}', "
                f"imp.alias = {repr(imp.alias)};"
            )
            statements.append(
                f"MATCH (file:File {{path: '{f.path}'}}), "
                f"(imp:Import {{qualified_name: '{safe_qname}'}}) "
                f"MERGE (file)-[:IMPORTS]->(imp);"
            )
        
        for cls in f.classes:
            safe_qname = cls.qualified_name.replace("'", "\\'")
            safe_doc = cls.docstring.replace("'", "\\'").replace("\n", " ")
            statements.append(
                f"MERGE (cls:Class {{qualified_name: '{safe_qname}'}}) "
                f"SET cls.name = '{cls.name}', "
                f"cls.docstring = '{safe_doc}', "
                f"cls.line_start = {cls.line_start}, "
                f"cls.line_end = {cls.line_end};"
            )
            statements.append(
                f"MATCH (file:File {{path: '{f.path}'}}), "
                f"(cls:Class {{qualified_name: '{safe_qname}'}}) "
                f"MERGE (file)-[:CONTAINS]->(cls);"
            )
            
            for method in cls.methods:
                safe_mname = method.qualified_name.replace("'", "\\'")
                safe_sig = method.signature.replace("'", "\\'")
                safe_mdoc = method.docstring.replace("'", "\\'").replace("\n", " ")
                statements.append(
                    f"MERGE (fn:Function {{qualified_name: '{safe_mname}'}}) "
                    f"SET fn.name = '{method.name}', "
                    f"fn.signature = '{safe_sig}', "
                    f"fn.docstring = '{safe_mdoc}', "
                    f"fn.line_start = {method.line_start}, "
                    f"fn.line_end = {method.line_end}, "
                    f"fn.is_async = {str(method.is_async).lower()}, "
                    f"fn.is_method = true;"
                )
                statements.append(
                    f"MATCH (cls:Class {{qualified_name: '{safe_qname}'}}), "
                    f"(fn:Function {{qualified_name: '{safe_mname}'}}) "
                    f"MERGE (cls)-[:CONTAINS]->(fn);"
                )
        
        for func in f.functions:
            safe_qname = func.qualified_name.replace("'", "\\'")
            safe_sig = func.signature.replace("'", "\\'")
            safe_doc = func.docstring.replace("'", "\\'").replace("\n", " ")
            statements.append(
                f"MERGE (fn:Function {{qualified_name: '{safe_qname}'}}) "
                f"SET fn.name = '{func.name}', "
                f"fn.signature = '{safe_sig}', "
                f"fn.docstring = '{safe_doc}', "
                f"fn.line_start = {func.line_start}, "
                f"fn.line_end = {func.line_end}, "
                f"fn.is_async = {str(func.is_async).lower()}, "
                f"fn.is_method = false;"
            )
            statements.append(
                f"MATCH (file:File {{path: '{f.path}'}}), "
                f"(fn:Function {{qualified_name: '{safe_qname}'}}) "
                f"MERGE (file)-[:CONTAINS]->(fn);"
            )
    
    return "\n".join(statements)


def index_to_memgraph(files: List[FileDef], uri: str, user: str, password: str):
    """Index files directly to Memgraph."""
    if not DRIVER_AVAILABLE:
        logger.error("neo4j driver not available")
        return
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            for f in files:
                session.run(
                    """
                    MERGE (file:File {path: $path})
                    SET file.name = $name,
                        file.language = $language,
                        file.lines = $lines,
                        file.indexed_at = datetime()
                    """,
                    path=f.path, name=f.name, language=f.language, lines=f.lines
                )
                
                for imp in f.imports:
                    session.run(
                        """
                        MERGE (imp:Import {qualified_name: $qname})
                        SET imp.module = $module, imp.alias = $alias
                        WITH imp
                        MATCH (file:File {path: $path})
                        MERGE (file)-[:IMPORTS]->(imp)
                        """,
                        qname=imp.qualified_name, module=imp.module,
                        alias=imp.alias, path=f.path
                    )
                
                for cls in f.classes:
                    session.run(
                        """
                        MERGE (cls:Class {qualified_name: $qname})
                        SET cls.name = $name,
                            cls.docstring = $docstring,
                            cls.line_start = $line_start,
                            cls.line_end = $line_end
                        WITH cls
                        MATCH (file:File {path: $path})
                        MERGE (file)-[:CONTAINS]->(cls)
                        """,
                        qname=cls.qualified_name, name=cls.name,
                        docstring=cls.docstring, line_start=cls.line_start,
                        line_end=cls.line_end, path=f.path
                    )
                    
                    for method in cls.methods:
                        session.run(
                            """
                            MERGE (fn:Function {qualified_name: $qname})
                            SET fn.name = $name,
                                fn.signature = $signature,
                                fn.docstring = $docstring,
                                fn.line_start = $line_start,
                                fn.line_end = $line_end,
                                fn.is_async = $is_async,
                                fn.is_method = true
                            WITH fn
                            MATCH (cls:Class {qualified_name: $cls_qname})
                            MERGE (cls)-[:CONTAINS]->(fn)
                            """,
                            qname=method.qualified_name, name=method.name,
                            signature=method.signature, docstring=method.docstring,
                            line_start=method.line_start, line_end=method.line_end,
                            is_async=method.is_async, cls_qname=cls.qualified_name
                        )
                
                for func in f.functions:
                    session.run(
                        """
                        MERGE (fn:Function {qualified_name: $qname})
                        SET fn.name = $name,
                            fn.signature = $signature,
                            fn.docstring = $docstring,
                            fn.line_start = $line_start,
                            fn.line_end = $line_end,
                            fn.is_async = $is_async,
                            fn.is_method = false
                        WITH fn
                        MATCH (file:File {path: $path})
                        MERGE (file)-[:CONTAINS]->(fn)
                        """,
                        qname=func.qualified_name, name=func.name,
                        signature=func.signature, docstring=func.docstring,
                        line_start=func.line_start, line_end=func.line_end,
                        is_async=func.is_async, path=f.path
                    )
                
                logger.info(f"Indexed: {f.path}")
    
    finally:
        driver.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/index_code.py <path> [--output cypher.txt]")
        print("       python scripts/index_code.py src/")
        print("       python scripts/index_code.py src/agent/router.py --output out.cypher")
        sys.exit(1)
    
    target_path = Path(sys.argv[1])
    output_file = None
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not target_path.exists():
        logger.error(f"Path does not exist: {target_path}")
        sys.exit(1)
    
    base_path = target_path.parent if target_path.is_file() else target_path.parent
    
    files_to_parse = []
    if target_path.is_file():
        files_to_parse.append(target_path)
    else:
        files_to_parse = list(target_path.rglob("*.py"))
    
    logger.info(f"Parsing {len(files_to_parse)} Python files...")
    
    parsed_files = []
    for file_path in files_to_parse:
        if "__pycache__" in str(file_path):
            continue
        result = parse_file(file_path, base_path)
        if result:
            parsed_files.append(result)
    
    logger.info(f"Successfully parsed {len(parsed_files)} files")
    
    total_classes = sum(len(f.classes) for f in parsed_files)
    total_functions = sum(len(f.functions) + sum(len(c.methods) for c in f.classes) for f in parsed_files)
    total_imports = sum(len(f.imports) for f in parsed_files)
    
    logger.info(f"Found: {total_classes} classes, {total_functions} functions, {total_imports} imports")
    
    cypher = generate_cypher(parsed_files)
    
    if output_file:
        Path(output_file).write_text(cypher)
        logger.info(f"Cypher written to: {output_file}")
    else:
        memgraph_uri = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
        memgraph_user = os.getenv("MEMGRAPH_USER", "")
        memgraph_pass = os.getenv("MEMGRAPH_PASSWORD", "")
        
        if DRIVER_AVAILABLE:
            logger.info(f"Indexing to Memgraph at {memgraph_uri}")
            index_to_memgraph(parsed_files, memgraph_uri, memgraph_user, memgraph_pass)
            logger.info("Indexing complete")
        else:
            print(cypher)


if __name__ == "__main__":
    main()
