# Protocol OMNI: Phase 4.5 Roadmap

> **Version**: v16.3.4  
> **Created**: 2026-01-24  
> **Updated**: 2026-01-25  
> **Status**: Lazarus Viable, Clawdbot Adoption Planned  
> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement tasks.

This roadmap formalizes the findings from the Paradigm Audit (2026-01-24) and defines the upgrade path for Protocol OMNI's infrastructure.

---

## Executive Summary

| Priority | Initiative | Target | Risk | Status |
|----------|------------|--------|------|--------|
| **P1** | Phoenix OTEL Upgrade | v0.14.0 | Low | ✅ DONE |
| **P1** | Script Internalization `/health/full` | Replace script | Low | ✅ DONE |
| **P1** | Memgraph AVX512 Stabilization | Zen 5 fix | Medium | ✅ DONE |
| **P2** | llama.cpp MXFP4 | >15 tok/s | Medium | ❌ BLOCKED (F-008) |
| **P2** | Docker Image Tag Pinning | Eliminate `:latest` | Low | ✅ DONE |
| **P2** | `mcp_sovereign_status` MCP tool | Replace script | Medium | ⚪ Planned |
| **P2** | Operation Lazarus (KTransformers) | sm_120 verified | Medium | ✅ VIABLE |
| **P2** | Operation Interface (Clawdbot) | Unified messaging | Low | ⚪ Planned |
| **P3** | NVIDIA Dynamo Sandbox | Evaluate | High | ⚪ Planned |
| **P3** | `/v1/introspect` + CronJob | Replace script | Medium | ⚪ Planned |
| **P3** | NVIDIA Driver 580.126.09 | Post-benchmark | Low | ⚪ Planned |
| **P4** | Monitor GLM-4.7 GGUF | When available | Low | 👀 Watching |

---

## P1: Operation Eagle Eye (Observability Upgrade) ✅ COMPLETE

### Objective
Upgrade Arize Phoenix OTEL from v0.1.0 to v0.14.0 to unlock new tracer API features.

### Changes Applied (2026-01-24)

| Package | Before | After | Status |
|---------|--------|-------|--------|
| arize-phoenix-otel | 0.1.0 | 0.14.0 | ✅ |
| opentelemetry-sdk | 1.39.0 | 1.39.1 | ✅ |
| fastapi | 0.115.0 | 0.128.0 | ✅ |
| langgraph | 1.0.0 | 1.0.7 | ✅ |
| mem0ai | 1.0.0 | 1.0.2 | ✅ |
| httpx | 0.27.0 | 0.28.1 | ✅ |

### Fix Applied
Missing `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable added to `docker/omni-stack.yaml`:
```yaml
OTEL_EXPORTER_OTLP_ENDPOINT: "http://arize-phoenix:4317"
OTEL_SERVICE_NAME: "omni-agent"
```

### Verification Results

| Check | Result |
|-------|--------|
| pydantic.v1 audit | PASS (no usage found) |
| Agent health | `tracing_enabled: true` ✅ |
| Phoenix health | Serving UI at :6006 ✅ |
| Test request | Qwen responded, trace exported ✅ |

---

## P1: Operation Internalize (Script → Endpoint) ✅ COMPLETE

### Objective
Replace `scripts/test_agent_connection.py` with native `/health/full` endpoint with Phoenix tracing.

### Changes Applied (2026-01-24)

| Action | Details |
|--------|---------|
| New endpoint | `GET /health/full` in `src/agent/main.py` |
| OTEL span | `health_full` with component check attributes |
| Archived | `scripts/test_agent_connection.py` → `scripts/_archive/` |

### Endpoint Response

```json
{
    "status": "healthy",
    "components": {
        "graph": {"status": "healthy", "tracing_enabled": true, "nodes": 8},
        "oracle": {"status": "healthy", "latency_ms": 51.7},
        "executor": {"status": "healthy", "latency_ms": 52.1},
        "memory": {"status": "healthy", "latency_ms": 51.4}
    },
    "routing_test": {
        "status": "pass",
        "routed_to": "qwen-executor",
        "match": true
    },
    "total_latency_ms": 408.8
}
```

### Verification Results

| Check | Result |
|-------|--------|
| All components | ✅ Healthy |
| Routing test | ✅ Qwen handled trivial prompt |
| Phoenix traces | ✅ 97 spans in `omni-agent` project |
| Script archived | ✅ `scripts/_archive/test_agent_connection.py` |

---

## P2: Operation Concrete Bunker (Tag Pinning) ✅ COMPLETE

### Objective
Eliminate all `:latest` Docker image tags to prevent production instability from upstream changes (Memgraph AVX512 crash proved this risk).

### Changes Applied (2026-01-25)

| Service | Before | After | Reason |
|---------|--------|-------|--------|
| letta | `letta/letta:latest` | `letta/letta:0.16.3` | Stability |
| qdrant | `qdrant/qdrant:latest` | `qdrant/qdrant:v1.16.0` | Stability |
| prometheus | `prom/prometheus:latest` | `prom/prometheus:v3.5.1` | Stability |
| grafana | `grafana/grafana:latest` | `grafana/grafana:12.4.0` | Stability |
| dcgm-exporter | `nvcr.io/.../dcgm-exporter:latest` | `4.4.2-4.7.1-ubuntu22.04` | Stability |
| node-exporter | `prom/node-exporter:latest` | `prom/node-exporter:v1.10.2` | Stability |
| arize-phoenix | `arizephoenix/phoenix:latest` | `arizephoenix/phoenix:version-12.31.2` | Stability |
| health-sidecar | `alpine:latest` | `alpine:3.21` | Stability |

### Lesson Learned
> The Memgraph crash (Exit 139 - SIGSEGV) was caused by an upstream `:latest` image pulling AVX512-compiled binaries incompatible with Zen 5. **Always pin to explicit version tags.**

### Verification
```bash
# Confirm no :latest tags remain
grep -r ":latest" docker/omni-stack.yaml | wc -l  # Should be 0
```

---

## P2: Operation Speed Demon (MXFP4 Benchmark) ❌ BLOCKED

### Status: BLOCKED (2026-01-25)

**Blocker**: DeepSeek-V3.2-Exp uses `deepseek3_2` architecture not supported by llama.cpp.

**See**: [F-008 in Lessons Learned](architecture/lessons-learned.md#f-008-mxfp4-deepseek-v32-exp-architecture-mismatch)

**What Happened**:
1. Downloaded 342GB MXFP4 model (18 chunks) via hf_transfer @ 57 MB/s
2. Reassembled into single GGUF (342GB)
3. llama.cpp failed: `unknown model architecture: 'deepseek3_2'`
4. Root cause: Model is DeepSeek-V3.2-Exp (experimental), not standard V3-0324

**Upstream Issue**: [ggml-org/llama.cpp#16331](https://github.com/ggml-org/llama.cpp/issues/16331)

**Cleanup Applied**:
- Deleted 684GB model files
- Removed sidecar service from `docker/omni-stack.yaml`
- Archived benchmark script

**Re-evaluate**: When llama.cpp adds `deepseek3_2` architecture support, or when a compatible MXFP4 quant of standard DeepSeek-V3-0324 becomes available.

---

### Original Objective (Archived)
Benchmark native MXFP4 quantization vs Q3_K_M to validate >15 tok/s target.

### Critical Corrections (2026-01-24 Paradigm Audit)

| Original Plan | Problem | Corrected Approach |
|---------------|---------|-------------------|
| Rebuild llama.cpp with MXFP4 flags | Binary already has MXFP4 support | Use existing `omni/llama-server:sm120-cuda13` |
| Use SM90 architecture | SM90 = Hopper (H100), not Blackwell | SM120 already configured |
| Build in Docker | VMM disabled = 3x regression | No rebuild needed |
| Quantize model manually | Takes hours | Download pre-quantized from HuggingFace |

### Context
- **Current**: Q3_K_M quantization @ 10.9 tok/s (298GB model)
- **Target**: MXFP4 quantization @ >15 tok/s (341GB model)
- **Source**: `stevescot1979/DeepSeek-V3.2-MXFP4-GGUF` on HuggingFace

### Pre-Flight Checklist

- [x] Verify llama.cpp has MXFP4 support (grep shows `GGML_TYPE_MXFP4` in build)
- [x] Install huggingface-cli on host
- [x] Add `deepseek-mxfp4` sidecar to `omni-stack.yaml` (profile: mxfp4-bench)
- [x] Create benchmark script (`scripts/benchmark_dragrace.py`)
- [ ] Download MXFP4 model (341GB, 18 chunks) - **IN PROGRESS**
- [ ] Run drag race benchmark
- [ ] Document results

### Implementation (Executed 2026-01-24)

**Step 1: Model Download** (running in screen session)
```bash
screen -S mxfp4_download
~/hf_env/bin/python /tmp/download_mxfp4.py
# Downloads to /nvme/models/deepseek-v3.2-mxfp4/
# Monitor: tail -f /tmp/mxfp4_download.log
```

**Step 2: Sidecar Configuration** (`docker/omni-stack.yaml`)
```yaml
deepseek-mxfp4:
  image: omni/llama-server:sm120-cuda13
  profiles: ["mxfp4-bench"]
  ports:
    - "8003:8000"
  # Same GPU allocation as production
```

**Step 3: Benchmark Procedure**
```bash
# Cannot run simultaneously - shared GPU memory!

# 1. Benchmark current production (Q3_K_M)
python3 ~/Protocol_Omni/scripts/benchmark_dragrace.py --port 8000 --name "Q3_K_M"

# 2. Stop production, start MXFP4
cd ~/Protocol_Omni/docker
docker compose -f omni-stack.yaml stop deepseek-v32
docker compose -f omni-stack.yaml --profile mxfp4-bench up -d deepseek-mxfp4
# Wait 10 minutes for model loading...

# 3. Benchmark MXFP4
python3 ~/Protocol_Omni/scripts/benchmark_dragrace.py --port 8003 --name "MXFP4"

# 4. Restore production
docker compose -f omni-stack.yaml stop deepseek-mxfp4
docker compose -f omni-stack.yaml up -d deepseek-v32
```

### Success Criteria

| Metric | Current (Q3_K_M) | Target (MXFP4) |
|--------|------------------|----------------|
| Generation speed | 10.9 tok/s | >15 tok/s |
| Prompt eval speed | 20.5 tok/s | >30 tok/s |
| Model quality | Baseline | No degradation |

### Pivot Back Criteria

**Revert if:**
- Generation speed <12 tok/s (failed to improve)
- Model quality degrades (hallucinations, incoherence)
- MXFP4 kernels cause CUDA errors
- Memory usage exceeds 128GB VRAM budget

**Rollback:**
```bash
# Simply keep using Q3_K_M model (no changes needed)
docker compose -f omni-stack.yaml stop deepseek-mxfp4
docker compose -f omni-stack.yaml up -d deepseek-v32
```

---

## P2: Operation Lazarus (KTransformers Resurrection) ✅ VIABLE

### Status: VIABLE (2026-01-25)

**Result:** PyTorch 2.11 Nightly (cu128) includes `sm_120` in `torch.cuda.get_arch_list()`.

**What Was Done:**
1. Created `docker/Dockerfile.ktransformers-lazarus` with PyTorch 2.11 Nightly
2. Added `lazarus` profile to `docker/omni-stack.yaml` (port 8004)
3. Migrated Docker storage to `/nvme` (3.6TB available)
4. Verified `sm_120` and `sm_120a` in arch list

**Commit:** `a6e158e feat(infra): implement Operation Lazarus`

**Next Phase:** Clone KTransformers, build with `TORCH_CUDA_ARCH_LIST="12.0"`, benchmark vs llama.cpp.

### Pre-Flight Checklist

- [x] Build sandbox container with PyTorch 2.11 Nightly (cu128)
- [x] Verify `torch.cuda.get_arch_list()` includes `sm_120`
- [ ] Load DeepSeek-V3.2 in KTransformers
- [ ] Run benchmark vs llama.cpp baseline
- [ ] Document GO/NO-GO decision

### Success Criteria

| Metric | Baseline (llama.cpp) | Target (KTransformers) |
|--------|---------------------|----------------------|
| Generation | 10.9 tok/s | >15 tok/s |
| First Token | ~2s | <1.5s |

### Risk

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SM120 support incomplete | High | Medium | Verify arch list before loading model |
| Performance regression | Medium | Low | Sandbox-only, no prod impact |

---

## P2: Operation Interface (Clawdbot Adoption)

### Status: PLANNED (2026-01-25)

**Strategic Decision:** Adopt [Clawdbot](https://github.com/cline/clawdbot) for the Interface Layer instead of building custom API handlers.

**Rationale:**
- Offload API maintenance to upstream project
- Leverage "Hubs" feature for unified messaging (Discord, Slack, Telegram)
- Focus Protocol OMNI on cognition, not plumbing

### Integration Requirements

| Component | Integration Point | Notes |
|-----------|------------------|-------|
| Mem0 | Memory persistence | Clawdbot must call Mem0 API for context |
| Memgraph | Relationship memory | Query entity relationships before responses |
| DeepSeek Oracle | LLM backend | Configure Clawdbot to use `:8000` |
| Qwen Executor | Fallback | Route trivial tasks to `:8002` |

### Pre-Flight Checklist

- [ ] Clone Clawdbot and review architecture
- [ ] Verify Hubs feature supports required platforms
- [ ] Design Mem0/Memgraph integration hooks
- [ ] Create `clawdbot` profile in `omni-stack.yaml`
- [ ] Document configuration for Protocol OMNI

### Risk

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Upstream abandonment | High | Low | Fork if necessary |
| Missing Mem0 hooks | Medium | Medium | Contribute PR or custom adapter |

---

## P3: Operation Dynamo (Distributed Inference)

### Objective
Evaluate NVIDIA Dynamo for distributed inference as potential llama.cpp replacement.

### Context
- NVIDIA Dynamo: Open-source distributed inference framework
- URL: https://github.com/ai-dynamo/dynamo
- Designed for multi-node, low-latency reasoning models

### Pre-Flight Checklist

- [ ] Read NVIDIA Dynamo documentation
- [ ] Verify Dynamo supports DeepSeek-V3.2 architecture
- [ ] Allocate sandbox environment (separate Docker network)

### Implementation Steps

1. **Clone and build Dynamo**
   ```bash
   cd ~
   git clone https://github.com/ai-dynamo/dynamo
   cd dynamo
   # Follow official build instructions
   ```

2. **Create sandbox Docker network**
   ```bash
   docker network create dynamo_sandbox
   ```

3. **Run Dynamo server with test model**
   ```bash
   # Start with smaller model first (Qwen 7B)
   # Benchmark latency and throughput
   ```

4. **Compare with llama.cpp**
   ```bash
   # Run identical prompts through both
   # Compare: latency, throughput, memory usage
   ```

### Success Criteria

| Metric | llama.cpp Baseline | Dynamo Target |
|--------|-------------------|---------------|
| Latency (first token) | ~2s | <1.5s |
| Throughput | 10.9 tok/s | >12 tok/s |
| Multi-GPU efficiency | 75/25 split | Native distributed |

### Pivot Back Criteria

**Do not adopt if:**
- Latency >200ms for first token (worse than llama.cpp)
- DeepSeek-V3.2 not supported
- Requires model conversion that loses quality
- Memory overhead exceeds VRAM budget
- Stability issues in 48-hour soak test

**Rollback:**
Continue using llama.cpp - no changes to production.

---

## Timeline

| Phase | Initiative | Start | Duration | Owner |
|-------|------------|-------|----------|-------|
| P1 | Eagle Eye (Phoenix) | 2026-01-24 | 1 day | Agent |
| P2 | Blackwell Boost (MXFP4) | 2026-01-27 | 3 days | Agent |
| P3 | Dynamo Sandbox | 2026-02-01 | 1 week | Agent |

---

## Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| FastAPI pydantic.v1 break | High | Medium | Audit before upgrade |
| MXFP4 model quality loss | High | Low | A/B test before deploy |
| Dynamo incompatibility | Medium | High | Sandbox only, no prod |
| Phoenix trace loss | Medium | Low | Immediate rollback plan |

---

## Appendix: Rollback Playbook

### Quick Rollback Commands

```bash
# Phoenix/FastAPI rollback
git checkout HEAD~1 -- src/agent/requirements.txt
rsync -avz src/agent/requirements.txt omni@192.168.3.10:~/Protocol_Omni/src/agent/
ssh omni@192.168.3.10 "cd ~/Protocol_Omni/docker && docker compose -f omni-stack.yaml build agent-orchestrator && docker compose -f omni-stack.yaml up -d --no-deps agent-orchestrator"

# llama.cpp rollback (no action needed - original still exists)
docker tag omni/llama-server:sm120-cuda13-backup omni/llama-server:sm120-cuda13

# Dynamo rollback (no action needed - sandbox only)
docker network rm dynamo_sandbox
```

---

*Document generated by Paradigm Audit 2026-01-24*
