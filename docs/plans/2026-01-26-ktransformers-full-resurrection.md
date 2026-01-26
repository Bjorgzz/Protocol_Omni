# KTransformers FULL Resurrection Plan

> **Date**: 2026-01-26  
> **Version**: v16.3.8  
> **Author**: Sentinel Audit Deep Research  
> **Status**: BLOCKED - GGUF FORMAT INCOMPATIBLE  
> **Priority**: P1

---

## Executive Summary

**Problem**: KTransformers Phase 3 achieved PARTIAL success - kt-kernel 0.5.1 works with sm_120, but `balance_serve` is blocked by `sched_ext` kernel dependency (requires kernel 6.12+, host has 6.8.0).

**Solution**: **SGLang + kt-kernel integration** bypasses balance_serve entirely. This is the production-grade path to FULL resurrection.

**NEW BLOCKER (v16.3.8)**: SGLang's GGUF loader (via transformers library) does NOT support deepseek2 architecture. kt-kernel requires BF16/FP16 safetensors as input - GGUF NOT supported for weight conversion.

**Decision Required**: Download DeepSeek-R1 HuggingFace BF16 weights (689GB) or wait for GGUF support.

**Performance Uplift**: 2.42x-4.09x speedups over llama.cpp baseline (10.9 tok/s → 26-45 tok/s theoretical).

---

## GGUF Blocker Details (v16.3.8 Discovery)

### Error Encountered
```
ValueError: GGUF model with architecture deepseek2 is not supported yet.
```
Source: `transformers/modeling_gguf_pytorch_utils.py:431`

### Root Cause Analysis
| Issue | Status | Owner |
|-------|--------|-------|
| SGLang Issue #4756 | OPEN | Upstream (transformers) |
| SGLang Issue #3973 | OPEN | Feature request |
| transformers GGUF deepseek2 | NOT IMPLEMENTED | HuggingFace |

### kt-kernel Weight Requirements
| Input Format | Supported | Output Format |
|--------------|-----------|---------------|
| BF16 (safetensors) | ✅ YES | INT4/INT8 |
| FP16 (safetensors) | ✅ YES | INT4/INT8 |
| FP8 (safetensors) | ✅ YES | INT4/INT8 |
| **GGUF (any quant)** | ❌ NO | N/A |

### Options
| Option | Size | Time | Risk | Recommendation |
|--------|------|------|------|----------------|
| Download HF BF16 weights | 689GB | 4-6 hrs | LOW | **RECOMMENDED** |
| Wait for GGUF support | 0 | UNKNOWN | N/A | NOT RECOMMENDED |
| Convert GGUF→safetensors | ~689GB | N/A | HIGH (lossy) | NOT RECOMMENDED |

---

## Research Findings

### The sched_ext Reality

| Claim | Reality |
|-------|---------|
| `sched_ext` is a pip package | **FALSE** - Kernel scheduler framework |
| Requires kernel 6.12+ | **TRUE** - CONFIG_SCHED_CLASS_EXT=y |
| Can be bypassed | **TRUE** - Use SGLang instead of balance_serve |
| Ubuntu 24.04 supports it | **RISKY** - PPA exists but breaks NVIDIA drivers |

### SGLang + kt-kernel Integration Status

| Aspect | Status | Evidence |
|--------|--------|----------|
| Issue #1785 (kt-kernel support) | **RESOLVED** | Confirmed working as of Jan 22, 2026 |
| Issue #11425 (upstream merge) | **IN PROGRESS** | Roadmap item, not blocking usage |
| DeepSeek-V3 support | **TESTED** | Benchmarked in SOSP '25 paper |
| DeepSeek-R1 support | **EXPECTED** | Same architecture (deepseek2) |

---

## Resurrection Paths (Ranked)

### Path A: SGLang + kt-kernel (RECOMMENDED)

**Risk**: LOW  
**Effort**: MEDIUM  
**Performance**: 2.42x-4.09x over llama.cpp

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│                  SGLang Server                   │
│         (OpenAI-compatible API :8000)            │
├─────────────────────────────────────────────────┤
│  Dense Layers     │     Expert Layers (MoE)      │
│  ───────────────  │  ─────────────────────────   │
│  GPU (Blackwell)  │  GPU (hot) + CPU (cold)      │
│  96GB VRAM        │  kt-kernel AMX/AVX512        │
└─────────────────────────────────────────────────┘
```

**Implementation**:
```bash
# 1. Install SGLang in Phase 3 container
pip install sglang[all]

# 2. Prepare CPU weights (INT8 quantization)
python -m kt_kernel.tools.convert_cpu_weights \
  --input-path /models/deepseek-r1/DeepSeek-R1-Q4_K_M \
  --input-type bf16 \
  --output /models/deepseek-r1-cpu-int8 \
  --quant-method int8

# 3. Launch SGLang with kt-kernel backend
python -m sglang.launch_server \
  --model deepseek-ai/DeepSeek-R1 \
  --trust-remote-code \
  --kt-method AMXINT8 \
  --kt-weight-path /models/deepseek-r1-cpu-int8 \
  --kt-cpuinfer 96 \
  --kt-threadpool-count 2 \
  --kt-num-gpu-experts 32 \
  --tensor-parallel-size 2 \
  --port 8000
```

**Why This Works**:
- SGLang handles GPU tensor parallelism (96GB + 32GB split)
- kt-kernel handles CPU expert inference (AMX/AVX512 on 9995WX)
- balance_serve is NOT used - SGLang replaces it entirely

---

### Path B: Custom kt-kernel Inference Script (FALLBACK)

**Risk**: MEDIUM  
**Effort**: HIGH  
**Performance**: Unknown (requires development)

This path uses kt-kernel directly without any server framework:

```python
import torch
import kt_kernel
from kt_kernel import KTMoEWrapper

# Direct kt-kernel inference (bypasses balance_serve)
wrapper = KTMoEWrapper(
    model_path="/models/deepseek-r1/DeepSeek-R1-Q4_K_M",
    backend="AMXINT8",
    num_threads=96
)

# Manual inference loop
output = wrapper.forward(input_ids)
```

**Limitation**: Requires significant custom code. No OpenAI-compatible API.

---

### Path C: Kernel Upgrade to 6.12+ (HIGH RISK)

**Risk**: HIGH  
**Effort**: LOW  
**Performance**: Enables native balance_serve

**Procedure**:
```bash
# Add sched-ext PPA
sudo add-apt-repository ppa:arighi/sched-ext
sudo apt update

# Install kernel 6.12 + headers
sudo apt install linux-image-6.12.13-arighi linux-headers-6.12.13-arighi

# Reboot
sudo reboot
```

**Known Issues**:
1. **NVIDIA driver breaks**: Mainline kernels don't have NVIDIA DKMS fixes
2. **No security updates**: Ubuntu doesn't support 6.12
3. **ROCm incompatible**: AMD explicitly doesn't support 6.12 on Ubuntu 24.04

**Verdict**: DO NOT USE IN PRODUCTION

---

## Implementation Plan

### Phase 1: Container Update (30 min)

Update `omni/ktransformers-lazarus:phase3` with SGLang:

```dockerfile
# Append to existing Phase 3 Dockerfile
RUN pip install --no-cache-dir \
    sglang[all] \
    flashinfer-python

# Runtime validation
CMD ["python", "-c", "import sglang; import kt_kernel; print('FULL RESURRECTION READY')"]
```

### Phase 2: Weight Preparation (2 hours)

Convert DeepSeek-R1 weights for hybrid inference:

```bash
# Inside container
python -m kt_kernel.tools.convert_cpu_weights \
  --input-path /models/deepseek-r1/DeepSeek-R1-Q4_K_M \
  --input-type q4_k_m \
  --output /models/deepseek-r1-cpu-weights \
  --quant-method int8
```

### Phase 3: Server Launch (10 min)

```bash
docker run -d \
  --name deepseek-r1-kt \
  --gpus all \
  -v /nvme/models:/models:ro \
  -p 8004:8000 \
  omni/ktransformers-lazarus:full \
  python -m sglang.launch_server \
    --model deepseek-ai/DeepSeek-R1 \
    --trust-remote-code \
    --kt-method AMXINT8 \
    --kt-weight-path /models/deepseek-r1-cpu-weights \
    --kt-cpuinfer 96 \
    --port 8000
```

### Phase 4: Benchmark & Compare (30 min)

```bash
# llama.cpp baseline (current)
curl http://localhost:8000/v1/completions -d '{"prompt": "Hello", "max_tokens": 100}'
# Expected: 10.9 tok/s

# SGLang + kt-kernel
curl http://localhost:8004/v1/completions -d '{"prompt": "Hello", "max_tokens": 100}'
# Expected: 26-45 tok/s (2.42x-4.09x improvement)
```

---

## Success Criteria

| Metric | Current (llama.cpp) | Target (SGLang+kt-kernel) | Status |
|--------|---------------------|---------------------------|--------|
| Generation Speed | 10.9 tok/s | >26 tok/s | PENDING |
| Prompt Eval | 20.5 tok/s | >50 tok/s | PENDING |
| API Compatibility | OpenAI | OpenAI | SAME |
| Model | DeepSeek-R1 Q4_K_M | DeepSeek-R1 (hybrid) | SAME |

---

## Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SGLang kt-kernel integration fails | HIGH | LOW | Fallback to llama.cpp |
| CUDA OOM on Blackwell | MEDIUM | MEDIUM | Reduce --kt-num-gpu-experts |
| Weight conversion fails | LOW | LOW | Use pre-converted weights from HF |
| Performance regression | MEDIUM | LOW | Benchmark before promoting |

---

## Rollback Plan

If SGLang + kt-kernel fails:

```bash
# Stop kt-kernel container
docker stop deepseek-r1-kt

# Start llama.cpp container (proven working)
docker start deepseek-r1
```

No changes to production required - llama.cpp remains the Oracle.

---

## References

1. [SGLang Issue #11425](https://github.com/sgl-project/sglang/issues/11425) - KTransformers Integration
2. [KTransformers Issue #1785](https://github.com/kvcache-ai/ktransformers/issues/1785) - SGLang support (RESOLVED)
3. [LMSYS Announcement](https://x.com/lmsysorg/status/1981103763441250387) - Official collaboration
4. [kt-kernel README](https://github.com/kvcache-ai/ktransformers/blob/main/kt-kernel/README.md) - SGLang integration docs
5. [SOSP '25 Paper](https://dl.acm.org/doi/10.1145/3731569.3764843) - Performance benchmarks

---

*Document generated by Sentinel Audit Deep Research - 2026-01-26*
