# ADR-0002: Use Docker Compose over Kubernetes

## Status

Accepted

## Date

2026-01-20

## Context

Protocol OMNI needed container orchestration for multiple services:
- LLM inference (llama-server)
- Observability (Arize Phoenix)
- Vector database (Qdrant)
- Graph database (Memgraph)
- MCP proxy

Initial architecture considered Kubernetes (k3s/Talos) for production-grade orchestration, but the complexity overhead for a single-node deployment was substantial.

## Decision

Use **Docker Compose** for all container orchestration. Kubernetes deferred until multi-node scaling required.

## Options Considered

1. **Kubernetes (k3s)**
   - Pros: Production-grade, auto-scaling, service mesh, industry standard
   - Cons: Complex for single-node, GPU operator complexity, overkill for current scale
   
2. **Talos Linux + Kubernetes**
   - Pros: Immutable OS, secure by default, declarative
   - Cons: Steep learning curve, driver compatibility concerns with Blackwell
   
3. **Docker Compose (chosen)**
   - Pros: Simple, well-understood, GPU passthrough works, restart policies sufficient
   - Cons: No auto-scaling, manual service discovery, single-node only

## Consequences

### Positive
- Simplified deployment and debugging
- Direct GPU access without operator complexity
- Fast iteration on container configurations
- Systemd integration for service persistence

### Negative
- No horizontal scaling
- Manual health monitoring
- No service mesh (rely on Docker networks)

### Neutral
- Stack definition in `docker/omni-stack.yaml`
- Kubernetes migration path preserved if needed

## References

- Related findings: S-004 (network isolation), S-011 (container naming)
- See also: [lessons-learned.md](../architecture/lessons-learned.md)
