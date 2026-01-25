# Operation Checkpoint Remediation Plan

## Objective
Synchronize documentation to v16.2.2 reality (NPS1, 10.9 t/s) and create the missing Verification Procedures Manual.

---

## Phase 1: Documentation Synchronization

### 1.1 Update README.md

**File**: `README.md`

| Line | Current | Change To |
|------|---------|-----------|
| 1 | `# Protocol OMNI v16.0` | `# Protocol OMNI v16.2.2` |
| 66 | `NPS=4` | `NPS=1 (Unified NUMA)` |
| 76 | `10.75 tok/s` | `10.9 tok/s` |

**Verification**: `grep -n "NPS\|tok/s\|v16" README.md`

### 1.2 Update concrete-bunker-doctrine.md

**File**: `docs/architecture/concrete-bunker-doctrine.md`

| Line | Current | Change To |
|------|---------|-----------|
| 101 | `7.57 tok/s` | `10.9 tok/s` |
| 125 | `7.57 tok/s (actual)` | `10.9 tok/s (actual)` |

Add NPS1 requirement note in "New Architecture" section.

**Verification**: `grep -n "tok/s" docs/architecture/concrete-bunker-doctrine.md`

### 1.3 Update lessons-learned.md

**File**: `docs/architecture/lessons-learned.md`

| Location | Current | Change To |
|----------|---------|-----------|
| S-001 | `10.75 tok/s` | `10.9 tok/s (NPS1 optimized)` |
| P-001 Trade-offs | `10.75 tok/s stable` | `10.9 tok/s stable` |

Add new success entry: **S-005: NPS1 BIOS Optimization (2.1x speedup)**

**Verification**: `grep -n "10.75\|10.9\|NPS" docs/architecture/lessons-learned.md`

---

## Phase 2: Create Verification Procedures Manual

### 2.1 Create New File

**File**: `docs/operations/verification_procedures.md`

**Content Structure**:

```markdown
# Protocol OMNI: Verification Procedures Manual

> **Version**: v16.2.2 NPS1 OPTIMIZED
> **Purpose**: Copy-pasteable commands to verify system state

## 1. Hardware Topology Verification

### 1.1 Confirm Single NUMA Node (NPS1)
```bash
ssh omni@192.168.3.10 "numactl --hardware | head -5"
```
**Expected Output**:
```
available: 1 nodes (0)
node 0 cpus: 0-191
node 0 size: 385807 MB
```

**FAIL Condition**: If `available: 4 nodes` → BIOS is NPS4, requires reconfiguration.

### 1.2 Confirm Memory Bandwidth (NPS1 Benefit)
```bash
ssh omni@192.168.3.10 "sudo mlc --latency_matrix"
```

## 2. BIOS Settings Verification

### 2.1 Confirm NPS1 via Redfish (BMC)
```bash
curl -sk -u admin:Aa135610 \
  https://192.168.3.202/redfish/v1/Systems/1/Bios | \
  jq '.Attributes | {NPS: .CbsDfCmnDramNpsSHP, Performance: .CbsCmnCpuGenCpb}'
```
**Expected**:
```json
{
  "NPS": "NPS1",
  "Performance": "Enabled"
}
```

## 3. Inference Speed Verification

### 3.1 The Golden Benchmark Command
```bash
ssh omni@192.168.3.10 "docker exec deepseek-v32 \
  llama-cli --model /models/deepseek-v3.2/DeepSeek-V3-0324-Q3_K_M.gguf \
  --prompt 'Hello' -n 128 --n-gpu-layers 19 --tensor-split 75,25 2>&1 | \
  grep -E 'eval|tok/s'"
```
**Expected**:
- `prompt eval: ≥20.0 tok/s`
- `eval: ≥10.9 tok/s`

**FAIL Condition**: `<7 tok/s` → Check NPS setting or CUDA VMM.

## 4. API Health Checks

### 4.1 Service Health Matrix
```bash
ssh omni@192.168.3.10 "
curl -sf http://localhost:8000/health && echo 'DeepSeek: OK' || echo 'DeepSeek: FAIL'
curl -sf http://localhost:8002/health && echo 'Qwen: OK' || echo 'Qwen: FAIL'
curl -sf http://localhost:8070/health && echo 'MCP Proxy: OK' || echo 'MCP Proxy: FAIL'
curl -sf http://localhost:8080/health && echo 'Agent Orch: OK' || echo 'Agent Orch: FAIL'
curl -sf http://localhost:6006/health && echo 'Phoenix: OK' || echo 'Phoenix: FAIL'
"
```

### 4.2 Inference Smoke Test
```bash
curl -X POST http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v3.2","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

## 5. Container Status Checks

### 5.1 Docker Sanity Check
```bash
ssh omni@192.168.3.10 "cd ~/Protocol_Omni/docker && docker compose -f omni-stack.yaml ps --format 'table {{.Name}}\t{{.Status}}'"
```

### 5.2 GPU Memory Allocation
```bash
ssh omni@192.168.3.10 "nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader"
```
**Expected**:
```
0, NVIDIA RTX PRO 6000, ~91000 MiB, 98304 MiB
1, NVIDIA RTX 5090, ~26000 MiB, 32768 MiB
```

## 6. Pre-Flight Checklist

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| NUMA Nodes | `numactl --hardware` | `available: 1 nodes` |
| NPS1 BIOS | Redfish query | `CbsDfCmnDramNpsSHP: NPS1` |
| DeepSeek Speed | Golden benchmark | `≥10.9 tok/s` |
| All Services | Health matrix | 5/5 OK |
| GPU Allocation | nvidia-smi | 91GB + 26GB |
```

---

## Phase 3: Ghost File Cleanup (Optional)

### 3.1 Archive Deprecated Scripts

Move to `scripts/_archive_deprecated/`:
- `scripts/benchmark-kt.sh`
- `scripts/build_ktransformers.sh`
- `scripts/kt-sglang-deploy.sh`

### 3.2 Archive Obsolete Compose Files

Move to `docker/_archive/`:
- `docker/glm-executor.yaml`
- `docker/Dockerfile.bleeding-edge`

---

## Verification (Definition of Done)

| Task | Verification Command |
|------|---------------------|
| README.md updated | `grep "NPS=1" README.md && grep "10.9 tok/s" README.md` |
| concrete-bunker updated | `grep "10.9 tok/s" docs/architecture/concrete-bunker-doctrine.md` |
| lessons-learned updated | `grep "NPS1\|10.9" docs/architecture/lessons-learned.md` |
| verification_procedures.md exists | `ls docs/operations/verification_procedures.md` |
| All commands in manual tested | Execute each command via SSH |

---

## Traceability Matrix

| Step | Target Files | Verification |
|------|--------------|--------------|
| 1.1 | README.md | grep NPS/tok/s |
| 1.2 | concrete-bunker-doctrine.md | grep tok/s |
| 1.3 | lessons-learned.md | grep NPS/tok/s |
| 2.1 | verification_procedures.md | file exists + commands runnable |
| 3.1-3.2 | scripts/, docker/ | git status shows moves |

---

## Risk Notes

- **BIOS Redfish Query**: Requires BMC credentials. Fallback: SSH + `numactl`.
- **Docker Exec Benchmark**: Container must be running. Add timeout (120s).
- **Ghost Cleanup**: Optional. Does not block green status.
