# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for Protocol OMNI.

## What is an ADR?

An ADR captures an important architectural decision along with its context and consequences. ADRs are immutable once accepted — if a decision changes, create a new ADR that supersedes the old one.

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-0001](0001-use-llamacpp-as-baseline.md) | Use llama.cpp as inference baseline | Accepted | 2026-01-19 |
| [ADR-0002](0002-use-docker-compose.md) | Use Docker Compose over Kubernetes | Accepted | 2026-01-20 |
| [ADR-0003](0003-use-cpu-executor-for-coding.md) | Use CPU executor for coding model | Superseded | 2026-01-21 |
| [ADR-0004](0004-use-phoenix-for-observability.md) | Use Arize Phoenix over Langfuse | Accepted | 2026-01-22 |
| [ADR-0005](0005-use-gguf-weights-format.md) | Use GGUF weights over HF formats | Accepted | 2026-01-23 |

## Creating a New ADR

1. Copy `_template.md` to `NNNN-verb-noun.md`
2. Fill in all sections
3. Add to index above
4. Link from AGENTS.md if relevant

## Related Documentation

- [AGENTS.md](../../AGENTS.md) — System status and routing
- [lessons-learned.md](../architecture/lessons-learned.md) — Historical findings archive
- [GitHub Issues](https://github.com/Bjorgzz/Protocol_Omni/issues) — Active work tracking
