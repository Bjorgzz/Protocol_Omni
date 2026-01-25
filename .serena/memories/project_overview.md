# Protocol OMNI - Project Overview

**Version:** v16.0 SOVEREIGN COGNITION  
**Purpose:** Self-evolving autonomous AI agent infrastructure

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI + Uvicorn
- **HTTP Client:** HTTPX (async)
- **Validation:** Pydantic v2
- **Container Runtime:** Docker CE 29.x
- **Orchestration:** Docker Compose / k3s
- **GPU:** CUDA 13.x, PyTorch 2.11.0+cu130
- **Inference Engine:** llama.cpp (Concrete Bunker Doctrine)

## Architecture

### Cognitive Models (v16.0)

| System | Model | Role | Profile | When Used |
|--------|-------|------|---------|-----------|
| System 2 | DeepSeek-V3.2 (671B, Q3_K_M) | Oracle | default | COMPLEX, TOOL_HEAVY |
| System 1 | Qwen2.5-Coder-7B (CPU, 192 threads) | Executor | cpu-executor | TRIVIAL, ROUTINE |
| Optional | Kimi K2 | External Tool Orchestrator | full | 200+ sequential tool calls |
| Failsafe | MiniMax M2.1 | Cold Storage | emergency | Emergency only |

**Default Routing:** `TRIVIAL/ROUTINE → Qwen` | `COMPLEX/TOOL_HEAVY → DeepSeek`

### LangGraph Cognitive Workflow (Phase 4.3)

```
START → parse → memory → classify → knowledge → {model} → store → metacog → END
```

Nodes:
- `parse`: Extract prompt from messages
- `memory`: Retrieve from Mem0
- `classify`: Sovereign Vocabulary complexity estimation
- `knowledge`: Memgraph code context
- `model`: Route to DeepSeek or Qwen
- `store`: Persist to Mem0
- `metacog`: 4-gate verification (optional)

### Zone Security

| Zone | Runtime | Privileged | Components |
|------|---------|------------|------------|
| Zone A (Brain) | Standard Docker | Yes | llama.cpp, DeepSeek-V3.2 |
| Zone B (Hands) | Standard Docker | No | Agents, MCP Proxy, Mem0 |

### Network Isolation (Concrete Bunker)

- `omni-network`: General inter-service communication
- `internal_brain`: Isolated network for Oracle (egress via mcp-proxy only)

## Core Components

| Module | Port | Purpose |
|--------|------|---------|
| `src/agent/graph.py` | - | LangGraph cognitive workflow |
| `src/agent/main.py` | 8080 | FastAPI wrapper + OTEL |
| `src/agent/nodes/*.py` | - | Graph nodes (classification, inference, memory, etc.) |
| `src/mcp_proxy/gateway.py` | 8070 | MCP Security Gateway (Default Deny) |
| `src/memory/mem0_client.py` | - | Mem0 integration |
| `src/knowledge/memgraph_client.py` | - | Code knowledge graph |
| `src/metacognition/engine.py` | 8011 | 4-gate verification |
| `src/gepa/evolution.py` | 8010 | Pareto-optimal prompt evolution |

## Key Files

- `docker/omni-stack.yaml` - Master Docker Compose
- `k8s/zone-a-inference.yaml` - Production k8s deployment
- `config/mcp-allowlist.yaml` - MCP tool permissions
- `config/gepa.yaml` - GEPA evolution config

## Hardware Target

- **Host:** `192.168.3.10` (omni-prime)
- **CPU:** AMD Threadripper 9995WX (96 cores, Zen5 AVX-512)
- **RAM:** 384GB DDR5-6400 (4 NUMA nodes)
- **GPU0:** RTX PRO 6000 Blackwell 96GB
- **GPU1:** RTX 5090 32GB

## Phase 4 Services

| Service | Port | Status |
|---------|------|--------|
| LangGraph Agent | 8080 | LIVE |
| Mem0 | 8050 | LIVE |
| MCP Proxy | 8070 | LIVE |
| Arize Phoenix | 6006 | LIVE |
| TRT-Sandbox | 8001 | profile: trt-sandbox |