---
name: sentinel-doc-sync
description: Ensures Protocol Omni documentation (AGENTS.md, plans) and ByteRover memory stay synchronized with code changes.
---

# Sentinel Documentation Sync

**When to use:**
- After ANY code change, deployment, or operational shift.
- When the user asks "status update" or "sync docs".
- Before marking a task as "DONE".
- Before ending a session or context handoff.

## The Mandate
Code, Documentation, and Memory are one. If code changes but `AGENTS.md` or ByteRover does not, the system is broken.

## Synchronization Checklist

### 1. The Routing Table (`AGENTS.md`)
- [ ] **Status**: Update the "Status" table (e.g., "HF DOWNLOAD ACTIVE").
- [ ] **Phase**: Verify "Current Phase" matches the roadmap.
- [ ] **Directives**: Did we learn a new "No-Go" rule? Add it.

### 2. The Plan (`docs/plans/`)
- [ ] **Progress**: Mark completed steps in the active plan file.
- [ ] **Blockers**: Record any new blockers (e.g., "GGUF Incompatible").
- [ ] **New Artifacts**: Link any new scripts or containers created.

### 3. The Internal Memory (`docs/architecture/lessons-learned.md`)
- [ ] **Failures**: If something failed (e.g., "GGUF load error"), log it as an F-XXX entry.
- [ ] **Discoveries**: Log successful configs (e.g., "Use snapshot_download for HF").

### 4. The External Memory (ByteRover) [MANDATORY]
- [ ] **Curate**: Run `brv curate "v16.x: <What changed>" --files <relevant-paths>`
- [ ] **Scope**: Include files that contain new patterns, configs, or learnings.
- [ ] **Context**: Summary should be queryable by future agents.

```bash
# Example curations
brv curate "v16.4.2: SGLang FP8 loading with 300GB CPU offload" --files docs/plans/2026-01-26-ktransformers-full-resurrection.md
brv curate "v16.4.2: Verdent shell restrictions resolved via Bash(*) wrapper" --files docs/architecture/lessons-learned.md
```

## Execution Order

```
┌─────────────────────────────────────────┐
│  1. UPDATE DOCS                         │
│     AGENTS.md → plans/ → lessons-learned│
├─────────────────────────────────────────┤
│  2. CURATE TO BYTEROVER                 │
│     brv curate "<summary>" --files <path>│
├─────────────────────────────────────────┤
│  3. VERIFY (if ending session)          │
│     brv status                          │
└─────────────────────────────────────────┘
```

## Anti-Patterns (Do Not Do)
- ❌ updating code without updating `AGENTS.md`
- ❌ writing "TODO: update docs later"
- ❌ vague status updates ("worked on stuff") -> Be specific ("Downloaded 1.2TB weights")
- ❌ skipping `brv curate` before session end (loses cross-session memory)
- ❌ curating without specific file references (makes knowledge unqueryable)
