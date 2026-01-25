# Phase 2 Evaluation: ik_llama.cpp Performance Testing

> **Date**: 2026-01-22  
> **Status**: FAILED - Reverted to production llama.cpp  
> **Version**: Protocol OMNI v15.1

## Executive Summary

ik_llama.cpp was evaluated as a potential performance upgrade from standard llama.cpp. Despite successful build with sm_120 (Blackwell) kernels and NCCL support, the benchmark showed a **significant performance regression** compared to production.

| Metric | Target | ik_llama.cpp | llama.cpp (Production) |
|--------|--------|--------------|------------------------|
| Generation (tok/s) | ≥20 | 6.10-6.56 | 10.75 |
| Prompt Eval (tok/s) | ≥100 | ~9.76 | ~100 |

**Decision**: ABORT Phase 2 - Retain production llama.cpp.

## Root Cause Analysis

### Why ik_llama.cpp Underperformed

ik_llama.cpp's key performance features are optimized for **symmetric GPU clusters**:

| Feature | Designed For | Our Setup |
|---------|--------------|-----------|
| **Split Mode Graph** | Symmetric TP across identical GPUs | Asymmetric 96GB + 32GB |
| **NCCL Multi-GPU** | NVLink/P2P between enterprise GPUs | Consumer cards with P2P disabled |
| **FlashMLA** | Memory-bound operations | Already using Flash Attention |

Our asymmetric setup (RTX PRO 6000 + RTX 5090) uses **pipeline parallelism** via `--tensor-split 75,25`, not tensor parallelism. The NCCL overhead for layer-based splitting actually *hurts* performance.

### The Geometry Problem (User Identified)

From plan audit:
> "TP might fail due to geometry... trying to load ~45GB onto 32GB GPU"

- Tensor Parallelism requires 50/50 split (matrix operations)
- Our GPUs: 96GB vs 32GB (3:1 asymmetry)
- Pipeline Parallelism (bucket filling) is the only viable option
- ik_llama.cpp optimizations don't benefit pipeline parallelism

## Build Artifacts

### Dockerfile.ik-blackwell (Functional)

Successfully built with fixes for:
1. **Held packages**: `--allow-change-held-packages` for NCCL
2. **CUDA stubs**: Symlink approach for build-time libcuda.so
3. **Library paths**: All .so files (libggml.so, libllama.so, libmtmd.so)
4. **Runtime deps**: libgomp1, libnccl2

### Verified sm_120 Kernels

```bash
$ cuobjdump build/ggml/src/libggml.so 2>&1 | grep "arch"
arch = sm_120
arch = sm_120
# ... (multiple sm_120 entries)
```

## Benchmark Results

### ik_llama.cpp (Sandbox)

```
GPU Configuration:
- CUDA0 (Blackwell): 81GB / 97GB used
- CUDA1 (5090): 23GB / 32GB used
- Layers on GPU: 19/62

Performance:
- eval time = 16382.37 ms / 100 tokens (163.82 ms/token, 6.10 tok/s)
- eval time = 2133.36 ms / 14 tokens (152.38 ms/token, 6.56 tok/s)
```

### llama.cpp (Production Baseline)

```
Performance:
- Generation: 10.75 tok/s
- Prompt Eval: ~100 tok/s
```

## Lessons Learned

1. **Asymmetric GPU clusters are special cases** - Most multi-GPU optimizations assume identical hardware
2. **NCCL P2P disabled is a significant constraint** - Consumer Blackwell cards lack enterprise interconnects
3. **Pipeline parallelism != Tensor parallelism** - Different parallelism strategies have different optimal software

## Recommendations

### Short-Term (Current Production)
- Retain llama.cpp with current configuration
- 10.75 tok/s exceeds the minimum viable threshold (7.57 tok/s)

### Medium-Term Options
1. **Wait for upstream llama.cpp improvements** - sm_120 optimizations are being actively developed
2. **Single-GPU mode** - Use Blackwell only, trade capacity for simplicity
3. **Quantization upgrade** - Consider Q4_K_M if we can fit in 128GB VRAM

### Long-Term
- If upgrading to symmetric GPU cluster (2x Blackwell), re-evaluate ik_llama.cpp
- Monitor vLLM Blackwell support (currently sm_100 issues)

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `docker/Dockerfile.ik-blackwell` | Created | Build recipe (retained for reference) |
| `docker/omni-stack.yaml` | Modified | Added deepseek-v32-ik service (profile: phase2-sandbox) |
| `docs/architecture/phase2-ik-llama-evaluation.md` | Created | This document |

## Rollback Executed

```bash
docker stop deepseek-v32-ik
docker rm deepseek-v32-ik
docker start deepseek-v32
# Production restored: deepseek-v32 (health: starting)
```

---

*Protocol OMNI v15.1 - Concrete Bunker Doctrine confirmed: llama.cpp remains the production inference engine.*
