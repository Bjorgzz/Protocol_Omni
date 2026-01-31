# ADR-0004: Use Arize Phoenix over Langfuse

## Status

Accepted

## Date

2026-01-22

## Context

Protocol OMNI required observability for LLM inference including:
- Trace visualization
- Token usage tracking
- Latency monitoring
- Prompt/response logging

Langfuse was initially evaluated but had limitations for local deployment.

## Decision

Use **Arize Phoenix** for LLM observability with OpenTelemetry integration.

## Options Considered

1. **Langfuse**
   - Pros: Purpose-built for LLM ops, good UI, active development
   - Cons: Cloud-first design, self-hosted requires PostgreSQL, heavier footprint
   
2. **Arize Phoenix (chosen)**
   - Pros: Local-first, OTEL native, lightweight, good trace visualization
   - Cons: Fewer features than Langfuse, smaller community
   
3. **Custom OTEL + Jaeger**
   - Pros: Full control, standard tooling
   - Cons: More setup, no LLM-specific features

## Consequences

### Positive
- Lightweight deployment (single container)
- Native OpenTelemetry support
- Good trace visualization for debugging

### Negative
- Fewer LLM-specific analytics than Langfuse
- Smaller ecosystem

### Neutral
- OTEL traces exportable to other backends if needed

## References

- Related findings: P-004
- External: [Arize Phoenix](https://github.com/Arize-ai/phoenix)
- See also: [lessons-learned.md](../architecture/lessons-learned.md)
