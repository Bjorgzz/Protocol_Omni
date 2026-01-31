# ADR-0005: Use GGUF Weights over HuggingFace Formats

## Status

Accepted

## Date

2026-01-23

## Context

DeepSeek-R1 (671B MoE) is available in multiple weight formats:
- **HuggingFace FP8**: 642GB, requires SGLang/vLLM
- **Meituan INT8**: 642GB, SGLang optimized
- **GGUF Q4_K_M**: 377GB, llama.cpp native

The critical constraint: 384GB system RAM with ~584GB addressable (including swap). SGLang loads the full model into RAM before GPU offload, making both HF formats unusable (F-022).

## Decision

Use **GGUF quantized weights** (Q4_K_M) with llama.cpp for all inference.

## Options Considered

1. **HuggingFace FP8**
   - Pros: Higher precision, native format
   - Cons: 642GB > addressable RAM, SGLang required (F-020)
   
2. **Meituan INT8**
   - Pros: Optimized for SGLang, good precision
   - Cons: Still 642GB, same RAM constraint (F-022)
   
3. **GGUF Q4_K_M (chosen)**
   - Pros: 377GB fits in RAM+swap, streaming load (never needs full model), llama.cpp native
   - Cons: Lower precision than FP8/INT8, quantization artifacts

## Consequences

### Positive
- Model loads successfully with streaming
- 11.79 tok/s achieved (competitive with claimed INT8 performance)
- Swap usage manageable (~40GB during inference)
- Future MXFP4 upgrade path via GGUF re-quantization

### Negative
- Quantization reduces precision vs FP8
- Cannot use SGLang features (batching, tensor parallelism)
- Re-quantization needed for MXFP4 upgrade

### Neutral
- GGUF ecosystem mature and well-supported
- Multiple quantization levels available (Q4, Q6, Q8)

## References

- Related findings: F-020, F-022, S-028
- External: [GGUF spec](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- See also: [lessons-learned.md](../architecture/lessons-learned.md#f-022)
