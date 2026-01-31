# ADR-0003: Use CPU Executor for Coding Model

## Status

Superseded (by dual-GPU architecture, S-028)

## Date

2026-01-21

## Context

Initially, the coding model (GLM-4.7) was deployed on GPU alongside DeepSeek-R1. However, VRAM contention caused issues (F-005). The decision was made to run the coding model on CPU instead.

## Decision

~~Run coding model on CPU executor (Threadripper 9995WX)~~ **SUPERSEDED**: Now run Qwen2.5-Coder-32B on RTX 5090 (S-028).

## Options Considered

1. **GPU tensor-split (both models)**
   - Pros: GPU acceleration for both
   - Cons: VRAM contention, tensor-split overhead (F-005)
   
2. **CPU executor for coding (original choice)**
   - Pros: Frees GPU VRAM for main model, Threadripper has high throughput
   - Cons: 16.39 tok/s vs potential 48+ tok/s on GPU
   
3. **Separate GPU per model (current)**
   - Pros: Full GPU acceleration for both, no contention
   - Cons: Requires second GPU

## Consequences (Original)

### Positive
- DeepSeek-R1 gets full GPU VRAM
- CPU executor achieved 16.39 tok/s on Threadripper

### Negative
- Coding model slower than GPU-accelerated
- CPU thermal load increased

## Update (2026-01-30)

**Superseded by S-028**: Dual-GPU architecture deployed. Qwen2.5-Coder-32B now runs on RTX 5090 at **48.9 tok/s** (3x faster than CPU executor).

## References

- Related findings: F-005, S-002, S-028
- Supersedes: This ADR
- See also: [lessons-learned.md](../architecture/lessons-learned.md#s-028)
