# Protocol OMNI - Task Completion Checklist

## Before Marking Task Complete

### 1. Code Quality
```bash
# Lint
ruff check src/

# Format
ruff format src/

# Type check
mypy src/
```

### 2. Testing (if applicable)
```bash
pytest
```

### 3. Infrastructure Verification (if docker/k8s changes)
```bash
# SSH to host
ssh omni@192.168.3.10

# Check containers
docker compose -f ~/Protocol_Omni/docker/omni-stack.yaml ps

# Check health
curl http://localhost:8000/health
```

### 4. Memory Curation (MANDATORY)

**ByteRover (Local Mac):**
```bash
# Check current state
brv status

# Curate new pattern
brv curate "v15.0: <What changed and why>" --files <path/to/file>
```

**Serena Memory:**
```
Use write_memory tool to persist new discoveries
```

### 5. Git Hygiene
```bash
git status
git diff
```

## Definition of Done

1. Code passes lint/typecheck
2. Tests pass (if applicable)
3. Infrastructure verified via SSH (if infra changes)
4. Memory curated to ByteRover
5. No uncommitted changes unless intentional
