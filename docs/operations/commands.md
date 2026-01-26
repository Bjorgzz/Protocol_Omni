# Commands Reference

> Common CLI commands for Protocol OMNI

## Remote Execution (Primary Method)

Native SSH is enabled via Verdent's `permission.json` allowlist.

**Setup (one-time on Mac):**
```bash
# 1. Ensure SSH key auth is configured
ssh-copy-id omni@192.168.3.10
ssh-add --apple-use-keychain ~/.ssh/id_ed25519

# 2. Create Verdent permission allowlist (CORRECT FORMAT with Bash() wrapper)
cat > ~/.verdent/permission.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(ssh omni@192.168.3.10 *)",
      "Bash(ssh -o BatchMode=yes omni@192.168.3.10 *)",
      "Bash(scp * omni@192.168.3.10:*)"
    ],
    "deny": []
  }
}
EOF
```

**Usage (AI agents can run directly, full shell syntax supported):**
```bash
ssh -o BatchMode=yes omni@192.168.3.10 "hostname"
ssh -o BatchMode=yes omni@192.168.3.10 "docker ps"
ssh -o BatchMode=yes omni@192.168.3.10 "nohup docker build ... > /tmp/log 2>&1 &"
```

**Why this works:** The `Bash()` wrapper in `permissions.allow` tells Verdent to treat matched commands as fully trusted, bypassing both sandbox AND injection detection.

**Fallback:** `mcp_ssh-mcp_ssh_execute` (MCP SSH tool) - for when permission.json is not configured

---

## SSH Access (Manual)

```bash
# SSH to omni-prime host
ssh omni@192.168.3.10

# With key
ssh -i ~/.ssh/id_ed25519 omni@192.168.3.10
```

## Docker Compose

### Stack Management

```bash
cd ~/Protocol_Omni/docker

# Start full stack
docker compose -f omni-stack.yaml --profile full up -d

# Start minimal (inference only)
docker compose -f omni-stack.yaml up -d deepseek-v32 metacognition agent-orchestrator

# Check status
docker compose -f omni-stack.yaml ps

# View logs
docker compose -f omni-stack.yaml logs -f deepseek-v32
docker compose -f omni-stack.yaml logs --tail 100 metacognition

# Restart service
docker compose -f omni-stack.yaml restart glm-executor

# Stop all
docker compose -f omni-stack.yaml down
```

### Individual Stacks

```bash
# Memory services only
docker compose -f memory-stack.yaml up -d

# Observability only
docker compose -f observability-stack.yaml up -d
```

## k3s (Production)

```bash
# Check pods
kubectl get pods -A

# View logs
kubectl logs -f inference-engine
kubectl logs -f -n agents agent-orchestrator

# Check Zone A
kubectl exec inference-engine -- nvidia-smi

# Check Zone B isolation
kubectl exec -n agents agent-orchestrator -- cat /proc/version

# Scale down (emergency)
kubectl scale deployment inference-engine --replicas=0
```

## GPU Operations

```bash
# GPU status
nvidia-smi

# GPU memory
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# CUDA version
nvcc --version

# Test GPU in container
docker run --rm --gpus all nvidia/cuda:13.0.1-base-ubi9 nvidia-smi

# PCIe link speed
nvidia-smi --query-gpu=name,pcie.link.gen.current,pcie.link.width.current --format=csv
```

## Health Checks

```bash
# DeepSeek-V3.2
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# GLM-4.7
curl http://localhost:8002/health

# MiniMax
curl http://localhost:8003/health

# Metacognition
curl http://localhost:8011/health

# Agent Orchestrator
curl http://localhost:8080/health

# Memory Services
curl http://localhost:8050/health  # Mem0
curl http://localhost:6333/health  # Qdrant
curl http://localhost:8283/health  # Letta

# Observability
curl http://localhost:6006/health   # Phoenix
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

## Inference Testing

```bash
# Simple chat
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "Hello"}]}'

# With streaming
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "Count to 10"}], "stream": true}'
```

## NUMA Verification

```bash
# Check NUMA binding (should show memory across all 4 nodes)
numastat -p $(pgrep -f ktransformers)

# Expected output:
#                   Node 0  Node 1  Node 2  Node 3
# MemUsed:          ~70GB   ~70GB   ~70GB   ~70GB
```

## Memory Systems

```bash
# Qdrant collections
curl http://localhost:6333/collections

# Memgraph (via console)
docker exec -it memgraph mgconsole

# Letta agents
curl http://localhost:8283/v1/agents
```

## Self-Improvement

```bash
# View Letta status
curl http://localhost:8283/health

# Check self-improvement metrics
curl http://localhost:9090/api/v1/query?query=letta_improvement_count
```

## Observability

```bash
# Prometheus targets
curl http://localhost:9090/api/v1/targets

# Phoenix traces
curl http://localhost:6006/health

# Grafana (browser)
open http://192.168.3.10:3000
```

## ByteRover (Local Mac)

```bash
# Check context tree
brv status

# Query knowledge
brv query "How is Zone A configured?"

# Curate new pattern
brv curate "v15.0: <description>" --files <path>
```

## Troubleshooting

```bash
# Container stats
docker stats

# System resources
htop
nvtop

# Check logs for errors
docker compose -f docker/omni-stack.yaml logs --tail 50 | grep -i error

# Network connectivity
curl -v http://192.168.3.10:8000/health
```
