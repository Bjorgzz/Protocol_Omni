# Protocol OMNI v14.0: SOVEREIGN GENESIS

Self-Evolving Autonomous Agent with Metacognitive Oversight

## Overview

Protocol OMNI v14.0 "SOVEREIGN GENESIS" is the next evolution of the OMNI assistant infrastructure, combining:

- **Trinity of Minds**: DeepSeek-R1 (Oracle) + Kimi K2 (Backup) + GLM-4.7 (Executor) + MiniMax (Failsafe)
- **GEPA Self-Evolution**: Genetic-Pareto prompt optimization via natural language reflection
- **Metacognition Engine**: 4-gate verification system to prevent confabulation
- **Phoenix Maneuver**: Self-healing infrastructure with automatic recovery

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 0: Hardware                         │
│  Threadripper 9995WX │ RTX 6000 96GB │ RTX 5090 32GB │384GB │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Layer 1: Cognitive Trinity                    │
│  DeepSeek-R1 (:8000) │ Kimi K2 (:8001) │ GLM-4.7 (:8002)   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              Layer 2: Meta-Cognitive Oversight               │
│           Metacognition (:8011) │ GEPA Engine (:8010)       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│               Layer 3: Agent Orchestration                   │
│    Agent Framework (:8080) │ MCP Tools │ Phoenix Sidecar    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Layer 4: Memory Systems                     │
│       Letta (:8283) │ Memgraph (:7687) │ Qdrant (:6333)     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Ubuntu 24.04 (bare metal)
- NVIDIA Driver 580.x
- Docker CE with NVIDIA Container Toolkit
- 384GB RAM, Dual Blackwell GPUs

### Start the Stack

```bash
# Create required directories
sudo mkdir -p /nvme/{models,prompts,eval/golden,gepa,phoenix,letta,memgraph,qdrant,prometheus,grafana}

# Download models (see APPENDIX in plan)
huggingface-cli download unsloth/DeepSeek-R1-GGUF --include "*DQ3_K_M*" --local-dir /nvme/models/deepseek-r1-dq3

# Start the full stack
cd docker
docker compose -f omni-stack.yaml up -d

# Check status
docker compose -f omni-stack.yaml ps
```

### Minimal Stack (DeepSeek-R1 only)

```bash
docker compose -f omni-stack.yaml up -d deepseek-r1 metacognition gepa-engine agent-orchestrator letta memgraph qdrant
```

## Key Components

| Service | Port | Description |
|---------|------|-------------|
| deepseek-r1 | 8000 | Primary Oracle - DeepSeek-R1 671B with Eagle speculative decoding |
| kimi-k2 | 8001 | Backup Oracle - Kimi K2 Thinking for tool orchestration |
| glm-executor | 8002 | Executor - GLM-4.7 with preserved thinking mode |
| minimax-failsafe | 8003 | Failsafe - MiniMax M2.1 for emergencies |
| gepa-engine | 8010 | GEPA self-evolution engine |
| metacognition | 8011 | Verification gates engine |
| agent-orchestrator | 8080 | Main agent with cognitive routing |
| letta | 8283 | Hierarchical memory (MemGPT) |
| memgraph | 7687 | Code knowledge graph |
| qdrant | 6333 | Vector embeddings |
| prometheus | 9090 | Metrics |
| grafana | 3000 | Dashboards |

## GEPA Self-Evolution

GEPA (Genetic-Pareto) automatically improves system prompts through:

1. **Trajectory Sampling**: Records agent executions
2. **Failure Reflection**: Oracle analyzes failures in natural language
3. **Variant Proposal**: Generates improved prompt variants
4. **Benchmarking**: Tests on golden dataset
5. **Pareto Selection**: Keeps non-dominated solutions
6. **Lesson Combination**: Merges complementary improvements

```bash
# Trigger evolution cycle manually
curl -X POST http://localhost:8010/evolve -H "Content-Type: application/json" \
  -d '{"current_prompts": {"deepseek-r1": "Your current system prompt..."}}'

# View Pareto frontier
curl http://localhost:8010/pareto-frontier
```

## Metacognition Gates

All agent outputs pass through 4 verification gates:

1. **Self-Check**: Does output align with prompt?
2. **Evidence**: Are claims supported by retrieved context?
3. **Confidence**: Is confidence above 0.85 threshold?
4. **Symbolic**: Are logic/math/code correct?

```bash
# Verify an output
curl -X POST http://localhost:8011/verify -H "Content-Type: application/json" \
  -d '{"agent_output": "...", "context": {"prompt": "..."}}'
```

## Phoenix Self-Healing

The Phoenix sidecar monitors agent health and auto-restarts on failure:

```bash
# Trigger manual restart
touch /nvme/phoenix/restart-requested

# Check Phoenix logs
docker logs phoenix-sidecar -f
```

## Project Structure

```
Protocol_Omni/
├── docker/
│   ├── omni-stack.yaml          # Master compose file
│   ├── deepseek-r1-eagle.yaml   # R1 standalone
│   ├── kimi-k2-oracle.yaml      # K2 standalone
│   ├── glm-executor.yaml        # GLM standalone
│   ├── phoenix-sidecar.yaml     # Self-healing
│   ├── memory-stack.yaml        # Letta + Memgraph + Qdrant
│   ├── observability-stack.yaml # Prometheus + Grafana
│   └── prometheus.yml           # Scrape config
├── src/
│   ├── agent/
│   │   └── router.py            # Cognitive routing logic
│   ├── metacognition/
│   │   ├── engine.py            # Verification pipeline
│   │   └── gates.py             # Individual gate implementations
│   └── gepa/
│       ├── evolution.py         # GEPA evolution engine
│       └── pareto.py            # Pareto frontier utilities
├── config/
│   └── gepa.yaml                # GEPA configuration
├── docs/
│   ├── OPERATION_IRON_SOVEREIGN.md  # Bare metal pivot plan
│   └── PROTOCOL_OMNI_V14.md         # This document
└── AGENTS.md                    # Operational doctrine
```

## License

MIT
