# Protocol OMNI - Suggested Commands

## Development (Local Mac)

```bash
# Install dependencies
pip install -e ".[dev]"

# Linting
ruff check src/

# Formatting  
ruff format src/

# Type checking
mypy src/

# Testing
pytest

# Run tests with coverage
pytest --cov=src
```

## Remote Operations (SSH to 192.168.3.10)

```bash
# SSH to host
ssh omni@192.168.3.10

# Check GPU status
nvidia-smi

# Docker Compose
cd ~/Protocol_Omni/docker

# Start minimal stack (DeepSeek only)
GRAFANA_ADMIN_PASSWORD=admin123 docker compose -f omni-stack.yaml up -d

# Start with CPU executor (Qwen)
GRAFANA_ADMIN_PASSWORD=admin123 docker compose -f omni-stack.yaml --profile cpu-executor up -d

# Start TRT sandbox (testing)
docker compose -f omni-stack.yaml --profile trt-sandbox up -d

# Start failsafe (emergency only)
docker compose -f omni-stack.yaml --profile emergency up -d

# View logs
docker compose -f omni-stack.yaml logs -f deepseek-v32

# Check container status
docker compose -f omni-stack.yaml ps

# Check specific service logs
docker logs agent-orchestrator --tail 50
```

## Health Checks

```bash
# DeepSeek-V3.2 (Oracle)
curl http://192.168.3.10:8000/health

# Qwen Executor (CPU)
curl http://192.168.3.10:8002/health

# Agent Orchestrator (LangGraph)
curl http://192.168.3.10:8080/health

# MCP Proxy (Security Gateway)
curl http://192.168.3.10:8070/health

# Mem0 (Memory Layer)
curl http://192.168.3.10:8050/health

# Phoenix (Observability)
curl http://192.168.3.10:6006/health

# Letta
curl http://192.168.3.10:8283/health

# Metacognition
curl http://192.168.3.10:8011/health
```

## Process Verification

```bash
# Check llama.cpp process
ssh omni@192.168.3.10 "pgrep -fa llama-server"

# Check NUMA allocation for llama.cpp (first matching PID)
ssh omni@192.168.3.10 'numastat -p $(pgrep -fo llama-server)'

# GPU memory usage
ssh omni@192.168.3.10 "nvidia-smi --query-gpu=memory.used,memory.total --format=csv"
```

## System Utils (macOS)

```bash
# Git operations
git status
git diff
git log --oneline -10

# ByteRover memory
brv status
brv query "How is <feature> implemented?"
brv curate "<context>" --files <path>
```

## Rebuilding Services

```bash
# SSH to host first
ssh omni@192.168.3.10
cd ~/Protocol_Omni/docker

# Rebuild specific service
GRAFANA_ADMIN_PASSWORD=admin123 docker compose -f omni-stack.yaml build <service>

# Restart without touching dependencies
docker compose -f omni-stack.yaml up -d --no-deps --force-recreate <service>
```