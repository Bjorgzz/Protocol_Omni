---
title: Sentinel Documentation Sync
description: Ensures Protocol Omni documentation (AGENTS.md, plans) stays strictly synchronized with code changes.
---

# Sentinel Documentation Sync

**When to use:**
- After ANY code change, deployment, or operational shift.
- When the user asks "status update" or "sync docs".
- Before marking a task as "DONE".

## The Mandate
Code and Documentation are one. If code changes but `AGENTS.md` does not, the system is broken.

## Synchronization Checklist

### 1. The Routing Table (`AGENTS.md`)
- [ ] **Status**: Update the "Status" table (e.g., "HF DOWNLOAD ACTIVE").
- [ ] **Phase**: Verify "Current Phase" matches the roadmap.
- [ ] **Directives**: Did we learn a new "No-Go" rule? Add it.

### 2. The Plan (`docs/plans/`)
- [ ] **Progress**: Mark completed steps in the active plan file.
- [ ] **Blockers**: Record any new blockers (e.g., "GGUF Incompatible").
- [ ] **New Artifacts**: Link any new scripts or containers created.

### 3. The Memory (`docs/architecture/lessons-learned.md`)
- [ ] **Failures**: If something failed (e.g., "GGUF load error"), log it as an F-XXX entry.
- [ ] **Discoveries**: Log successful configs (e.g., "Use snapshot_download for HF").

## Anti-Patterns (Do Not Do)
- ❌ updating code without updating `AGENTS.md`
- ❌ writing "TODO: update docs later"
- ❌ vague status updates ("worked on stuff") -> Be specific ("Downloaded 1.2TB weights")
