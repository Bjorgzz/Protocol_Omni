# Source Code

Python source code for Protocol OMNI v16.0.

## Modules

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `agent/` | LangGraph cognitive workflow | `graph.py`, `main.py`, `nodes/` |
| `memory/` | Mem0 persistent memory | `mem0_client.py` |
| `knowledge/` | Memgraph code graph | `memgraph_client.py` |
| `mcp_proxy/` | Security gateway | `gateway.py`, `allowlist.py`, `audit.py` |
| `metacognition/` | 4-gate verification (legacy) | `engine.py`, `gates.py` |

## Agent Module (v16.0)

Implements the LangGraph cognitive workflow:

```
parse → retrieve_memory → classify → retrieve_knowledge → call_model → store_memory → metacog → respond
```

### Nodes

| Node | File | Purpose |
|------|------|---------|
| `parse_request` | `graph.py` | Validate input, extract prompt |
| `classify_complexity` | `nodes/classification.py` | TRIVIAL/ROUTINE/COMPLEX/TOOL_HEAVY |
| `retrieve_memory` | `nodes/memory.py` | Mem0 lookup |
| `retrieve_knowledge` | `nodes/knowledge.py` | Memgraph code context |
| `call_model` | `nodes/inference.py` | HTTP client to llama.cpp |
| `store_memory` | `nodes/memory.py` | Mem0 persist |
| `metacog_verify` | `nodes/metacognition.py` | 4-gate verification |

### Routing Logic

```
TRIVIAL     → Qwen2.5-Coder-7B (:8002) - CPU Executor
ROUTINE     → Qwen2.5-Coder-7B (:8002) - 16.39 tok/s
COMPLEX     → DeepSeek-V3.2 (:8000) - Deep reasoning
TOOL_HEAVY  → DeepSeek-V3.2 (:8000) - Full context + knowledge
```

## Memory Module (v16.0)

Mem0 integration for persistent memory:

```python
from memory import Mem0Client

client = Mem0Client()
await client.store_memory("content", user_id="default")
result = await client.search_memory("query", user_id="default")
```

## Knowledge Module (v16.0)

Memgraph code knowledge graph:

```python
from knowledge import MemgraphClient

client = MemgraphClient()
symbols = client.find_symbol("CognitiveRouter")
refs = client.find_references("process")
context = client.get_code_context("where is router defined")
```

## MCP Proxy Module

Security gateway with Default Deny policy (v15.1):

- `gateway.py` - FastAPI application
- `allowlist.py` - YAML permission management
- `audit.py` - Prometheus metrics + structured logging

## Metacognition (4-Gate)

Response verification pipeline:

| Gate | Function |
|------|----------|
| Hallucination | Detect AI cop-out phrases |
| Completeness | Check for truncation markers |
| Length | Minimum substantive response |
| Coherence | Response addresses prompt |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest src/

# Lint
ruff check src/

# Type check
mypy src/
```

## Testing

```bash
# Run all tests
pytest

# Run specific module
pytest src/agent/

# With coverage
pytest --cov=src/
```

## Legacy Modules

| Module | Status | Notes |
|--------|--------|-------|
| `gepa/` | Legacy | Replaced by Letta/Mem0 |
| `agent/router_legacy.py` | Archived | Custom router (pre-LangGraph) |
