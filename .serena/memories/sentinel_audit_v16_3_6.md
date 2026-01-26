# Sentinel Audit v16.3.6 (2026-01-26)

## Critical Corrections - Lazarus Phase 2 Directive

| Original Claim | Reality | Severity |
|----------------|---------|----------|
| `pip install sched_ext` | **Kernel feature, NOT pip package** | BLOCKING |
| NPS4 optimal for 9995WX | **NPS1 gives 2.1x speedup** (S-005) | INCORRECT |
| sglang --kt-weight-path | **Integration not merged** (Issue #11425) | BLOCKING |
| Kernel 6.12+ available | **Host has 6.8.0** (Ubuntu 24.04) | BLOCKING |

## Host State Verified

| Component | Value |
|-----------|-------|
| Kernel | 6.8.0-90-generic |
| Ubuntu | 24.04 |
| NUMA | 1 node (NPS1) - **CORRECT** |
| GPU0 | Blackwell 96GB (idle) |
| GPU1 | 5090 32GB (idle) |

## sched_ext Reality

- **What it is**: Linux kernel scheduler extension framework (BPF-based)
- **Kernel config**: `CONFIG_SCHED_CLASS_EXT=y`
- **Minimum kernel**: 6.12+
- **NOT a pip package**: PyPI returns `{"message": "Not Found"}`
- **Source**: https://sched-ext.com, github.com/sched-ext/scx

## SGLang + kt-kernel Integration

- **Issue #1785**: "SGLang does not support kt-kernel"
- **Issue #11425**: Integration upstreaming in progress
- **Reddit consensus**: "Unified ecosystem... still need ktransformers cpu kernels"
- **Status**: WIP, not production-ready

## Lazarus Phase 3 Status

| Component | Status |
|-----------|--------|
| kt-kernel 0.5.1 | **WORKS** (sm_120 verified) |
| PyTorch 2.11 nightly | **WORKS** (cu128) |
| balance_serve | **BLOCKED** (needs sched_ext) |
| Full inference | **BLOCKED** |

## Recommended Path - UPDATED 2026-01-26

### PRIMARY: SGLang + kt-kernel (FULL RESURRECTION)

**Status**: ACTIONABLE  
**Performance**: 2.42x-4.09x over llama.cpp (26-45 tok/s theoretical)

**Key Discovery**: SGLang Issue #1785 is **RESOLVED** (Jan 22, 2026). kt-kernel support confirmed working.

**Implementation**:
```bash
# Install in Phase 3 container
pip install sglang[all]

# Launch with kt-kernel backend
python -m sglang.launch_server \
  --model deepseek-ai/DeepSeek-R1 \
  --kt-method AMXINT8 \
  --kt-weight-path /models/deepseek-r1-cpu-int8 \
  --kt-cpuinfer 96 \
  --port 8000
```

**Why This Works**: SGLang replaces balance_serve entirely. No sched_ext needed.

### FALLBACK: llama.cpp (10.9 tok/s, proven)

### DO NOT USE: Kernel 6.12 upgrade (breaks NVIDIA drivers)

**Full Plan**: `docs/plans/2026-01-26-ktransformers-full-resurrection.md`

## Container Status (2026-01-26)

| Service | Health |
|---------|--------|
| agent-orchestrator | Healthy |
| memgraph | Healthy (AVX512 fix applied) |
| mem0 | Healthy |
| metacognition | Healthy |
| gepa-engine | Healthy |
| letta | **Unhealthy** |
| qdrant | **Unhealthy** |
| mcp-proxy | Unhealthy |

## Native SSH Test

- Verdant allowlist works for most patterns
- `&&` chaining with some commands triggers injection detection
- MCP fallback available: `mcp_ssh-mcp`

---

## Cold Case Review (Layer 4)

| ID | Technology | Status | Notes |
|----|------------|--------|-------|
| F-001 | KTransformers | **PARTIAL** | kt-kernel 0.5.1 works, balance_serve blocked |
| F-001 | vLLM | **PARTIAL FIX** | v0.12 NVFP4 works, FlashMLA disabled on Blackwell |
| F-001 | SGLang | **STILL BLOCKED** | RMSNorm issues #7249, #14120 open |
| F-008 | deepseek3_2 | **PARTIAL FIX** | vLLM day-0 support, llama.cpp #16331 open |
| F-018 | balance_serve | **STILL BLOCKED** | Kernel 6.12+ required (host: 6.8.0) |

## System Versions

| Component | Installed | Latest | Gap |
|-----------|-----------|--------|-----|
| NVIDIA Driver | 580.95.05 | 580.126.09 | MINOR |
| LangGraph | 1.0.7 | 1.0.7 | CURRENT |
| Docker | 29.1.5 | Current | CURRENT |
| Kernel | 6.8.0-90 | 6.12+ (sched_ext) | MAJOR |

## Priority Actions

1. **P0**: Fix 4 unhealthy services (phoenix, letta, mcp-proxy, qdrant)
2. **P1**: Start DeepSeek-R1 inference (GPUs idle, model ready)
3. **P2**: Re-evaluate vLLM v0.12+ with NVFP4
4. **P3**: Upgrade driver 580.126.09 post-benchmark