# ADR-0001: Use llama.cpp as Inference Baseline

## Status

Accepted

## Date

2026-01-19

## Context

Protocol OMNI required a high-performance LLM inference engine for DeepSeek-R1 (671B MoE) on NVIDIA Blackwell GPUs (PRO 6000 + RTX 5090). Multiple options were evaluated:

- **KTransformers**: Claimed 30+ tok/s via DeepGEMM + speculative decoding
- **SGLang**: Production-grade serving with tensor parallelism
- **llama.cpp**: GGUF streaming, progressive layer loading

KTransformers (F-001) failed on Blackwell SM120 due to pre-compiled CUDA kernels. Multiple resurrection attempts ("Operation Lazarus") produced partial builds but the sched_ext dependency chain (F-023) blocked full inference. SGLang (F-022) was blocked because Meituan INT8 weights required 642GB > addressable RAM.

## Decision

Adopt **llama.cpp** with explicit SM120 compilation (`ARCHS=120a`) as the "Concrete Bunker" baseline. KTransformers remains a deferred upgrade path (F-027).

## Options Considered

1. **KTransformers v0.5.1**
   - Pros: 30+ tok/s claimed, speculative decoding, DeepGEMM optimizations
   - Cons: SM120 kernel rebuild required, sched_ext → prometheus-cpp → PhotonLibOS dependency chain, 4-8h fix effort
   
2. **SGLang + Meituan INT8**
   - Pros: Production-grade, tensor parallelism, automatic batching
   - Cons: 642GB weight size exceeds 584GB addressable RAM, loads full model before offload
   
3. **llama.cpp (chosen)**
   - Pros: GGUF streaming (never needs full model in RAM), SM120 native build works, stable baseline
   - Cons: Lower theoretical performance than KTransformers, no built-in speculative decoding

## Consequences

### Positive
- Stable 10.9 → 11.79 tok/s achieved after BIOS tuning
- Simplified deployment (single container per model)
- Dual-GPU architecture enabled (DeepSeek-R1 + Qwen-Coder)
- Foundation for future upgrades (MXFP4, speculative decoding)

### Negative
- Lost speculative decoding (KTransformers feature)
- Lost DeepGEMM tensor core optimizations
- Theoretical ceiling lower than KTransformers

### Neutral
- All future inference work builds on llama.cpp
- KTransformers upgrade path preserved for when ROI improves

## References

- Related findings: F-001, F-022, F-023, F-027, S-001
- External: [llama.cpp](https://github.com/ggml-org/llama.cpp)
- See also: [lessons-learned.md](../architecture/lessons-learned.md#f-001)
