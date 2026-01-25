// Memgraph Schema for Code Knowledge Graph
// Protocol OMNI Phase 4.4 - SOVEREIGN COGNITION
//
// Usage: mgconsole < scripts/memgraph-schema.cypher
// Or via Memgraph Lab: http://192.168.3.10:7444

// Clear existing data (optional - uncomment if needed)
// MATCH (n) DETACH DELETE n;

// Create constraints for unique identifiers
CREATE CONSTRAINT ON (f:File) ASSERT f.path IS UNIQUE;
CREATE CONSTRAINT ON (c:Class) ASSERT c.qualified_name IS UNIQUE;
CREATE CONSTRAINT ON (fn:Function) ASSERT fn.qualified_name IS UNIQUE;
CREATE CONSTRAINT ON (i:Import) ASSERT i.qualified_name IS UNIQUE;

// Create indexes for fast lookups
CREATE INDEX ON :File(name);
CREATE INDEX ON :File(language);
CREATE INDEX ON :Class(name);
CREATE INDEX ON :Function(name);
CREATE INDEX ON :Import(module);

// Node type descriptions:
//
// (:File)
//   - path: str (unique, absolute path)
//   - name: str (filename only)
//   - language: str (python, typescript, etc.)
//   - lines: int (line count)
//   - indexed_at: datetime
//
// (:Class)
//   - qualified_name: str (unique, e.g., "src.agent.router.CognitiveRouter")
//   - name: str (class name only)
//   - docstring: str (first paragraph)
//   - line_start: int
//   - line_end: int
//
// (:Function)
//   - qualified_name: str (unique, e.g., "src.agent.router.CognitiveRouter.route")
//   - name: str (function name only)
//   - signature: str (e.g., "async def route(self, request: AgentRequest) -> RoutingDecision")
//   - docstring: str (first paragraph)
//   - line_start: int
//   - line_end: int
//   - is_async: bool
//   - is_method: bool
//
// (:Import)
//   - qualified_name: str (unique, full import path)
//   - module: str (module name)
//   - alias: str (import alias if any)

// Edge type descriptions:
//
// (:File)-[:CONTAINS]->(:Class)
//   File contains class definition
//
// (:File)-[:CONTAINS]->(:Function)
//   File contains top-level function
//
// (:Class)-[:CONTAINS]->(:Function)
//   Class contains method
//
// (:Function)-[:CALLS]->(:Function)
//   Function calls another function
//
// (:File)-[:IMPORTS]->(:Import)
//   File imports a module
//
// (:Class)-[:INHERITS]->(:Class)
//   Class inherits from another class

// Example queries:
//
// Find all functions in a file:
// MATCH (f:File {path: $path})-[:CONTAINS*]->(fn:Function)
// RETURN fn.name, fn.signature
//
// Find all callers of a function:
// MATCH (caller:Function)-[:CALLS]->(target:Function {name: $name})
// RETURN caller.qualified_name, caller.signature
//
// Get class hierarchy:
// MATCH path = (child:Class)-[:INHERITS*]->(ancestor:Class)
// WHERE child.name = $class_name
// RETURN path
//
// Find all imports in a file:
// MATCH (f:File {path: $path})-[:IMPORTS]->(i:Import)
// RETURN i.module, i.alias
//
// Find functions with a specific pattern in name:
// MATCH (fn:Function)
// WHERE fn.name CONTAINS 'process'
// RETURN fn.qualified_name, fn.signature
