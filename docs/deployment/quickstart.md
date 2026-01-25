# Quickstart Guide

> Get Protocol OMNI running in 10 minutes

## Prerequisites

- Ubuntu 24.04 LTS (bare metal at 192.168.3.10)
- NVIDIA Driver 580.x with CUDA 13.x
- Docker CE 29.x with NVIDIA Container Toolkit
- SSH access from your workstation

## 1. Clone Repository

```bash
ssh omni@192.168.3.10

# Replace YOUR-ORG with actual organization
git clone https://github.com/YOUR-ORG/Protocol_Omni.git
cd Protocol_Omni
```

## 2. Prepare Storage

```bash
# Create required directories
sudo mkdir -p /nvme/{models,prompts,mem0,letta,memgraph,qdrant,prometheus,grafana}
sudo chown -R $USER:$USER /nvme
```

## 3. Download Models

```bash
# DeepSeek-V3.2 (DQ3_K_M quantization - ~281GB)
huggingface-cli download unsloth/DeepSeek-V3.2-GGUF \
  --include "*DQ3_K_M*" \
  --local-dir /nvme/models/deepseek-v3.2-dq3
```

## 4. Start Stack

```bash
cd docker

# Start full stack
docker compose -f omni-stack.yaml --profile full up -d

# Or minimal (DeepSeek-V3.2 + core services only)
docker compose -f omni-stack.yaml up -d deepseek-v32 metacognition agent-orchestrator mem0 qdrant
```

## 5. Verify Deployment

```bash
# Check services
docker compose -f omni-stack.yaml ps

# Test inference (wait 3-5 min for model load)
curl http://localhost:8000/health

# Test chat
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 6. Configure IDE

### Cursor / VS Code

```
API Base: http://192.168.3.10:8000/v1
API Key: sk-local
Model Name: deepseek-v3.2
```

### Continue.dev

```json
{
  "models": [{
    "title": "DeepSeek-V3.2 Local",
    "provider": "openai",
    "model": "deepseek-v3.2",
    "apiBase": "http://192.168.3.10:8000/v1",
    "apiKey": "sk-local"
  }]
}
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Model load timeout | Wait 5 min; 281GB takes time to load |
| CUDA version mismatch | Use PyTorch cu130 nightly |
| GPU not visible | Check `nvidia-smi` and container toolkit |
| OOM during load | Verify NUMA: `numactl --cpunodebind=0 --interleave=all` |

## Next Steps

- [Full Bare Metal Setup](bare-metal.md) - Complete installation guide
- [k3s Production](k3s-production.md) - Production deployment
- [Commands Reference](../operations/commands.md) - Common commands
- [AGENTS.md](../../AGENTS.md) - AI agent operational doctrine
