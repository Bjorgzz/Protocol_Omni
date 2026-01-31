---
name: sentinel-doc-sync
description: Ensures Protocol Omni documentation (AGENTS.md, README.md, plans) and ByteRover memory stay synchronized with code changes.
---

# Sentinel Documentation Sync v2

**When to use:**
- After ANY code change, deployment, or operational shift
- Before marking a task as "DONE"
- Before ending a session or context handoff

## The Mandate
Code, Documentation, and Memory are ONE. If code changes but docs do not, the system is broken.

---

## Pre-Work: Topic Lookup (MANDATORY)

**Before working on any area, agents MUST read the relevant topic section:**

| Task Area | Required Reading |
|-----------|-----------------|
| GPU / OC | [§1 GPU & Overclocking](docs/architecture/lessons-learned.md#1-gpu--overclocking) |
| PCIe / Slots | [§2 PCIe & Interconnect](docs/architecture/lessons-learned.md#2-pcie--interconnect) |
| BIOS / RAM | [§3 BIOS & Memory](docs/architecture/lessons-learned.md#3-bios--memory-tuning) |
| Inference | [§4 Inference Engines](docs/architecture/lessons-learned.md#4-inference-engines) |
| Docker | [§5 Docker & Containers](docs/architecture/lessons-learned.md#5-docker--containers) |
| Multi-GPU | [§6 Multi-GPU](docs/architecture/lessons-learned.md#6-multi-gpu-architecture) |
| Network | [§7 Network & Security](docs/architecture/lessons-learned.md#7-network--security) |
| Builds | [§8 Build & Dependencies](docs/architecture/lessons-learned.md#8-build--dependencies) |

---

## Synchronization Checklist

### 1. AGENTS.md [CRITICAL]
- [ ] **Version**: Increment (vX.Y.Z → vX.Y.Z+1)
- [ ] **Status Table**: Update phase, performance, GPU status
- [ ] **Recent Lessons**: Add S-XXX/F-XXX entry (keep last 10-15 only)
- [ ] **Directives**: New rule learned? Add it

### 2. README.md [CRITICAL]
- [ ] **Version Alignment**: MUST match AGENTS.md
- [ ] **Architecture Diagram**: Update if services changed
- [ ] **Performance Table**: Update throughput numbers

### 3. lessons-learned.md (Topic Archive)
- [ ] Add detailed entry to appropriate topic section
- [ ] Update Quick Reference table if new anti-pattern discovered

### 4. ByteRover [MANDATORY]
```bash
brv curate "vX.Y.Z: <summary>" --files AGENTS.md README.md docs/architecture/lessons-learned.md
```

---

## AGENTS.md Trimming Protocol

**When lessons exceed 15 entries:**
1. Move oldest entries to topic section in `lessons-learned.md`
2. Keep abbreviated summary in AGENTS.md with section link
3. Example: `- **2026-01-28 S-015-S-018**: BIOS work — see [§3](docs/architecture/lessons-learned.md#3-bios--memory-tuning)`

---

## Cleanup Check (PERIODIC)

```bash
# Check for obsolete directories
find . -maxdepth 2 -type d -name "_archive*" | head -5
find . -maxdepth 2 -type d -empty | head -5

# Verify ADR compliance
grep -r "DEPRECATED\|OBSOLETE" docs/ --include="*.md" | head -5
```

---

## Version Alignment Commands

```bash
# Check alignment (version-agnostic)
grep -E "^#.*v[0-9]+\.[0-9]+\.[0-9]+" AGENTS.md README.md

# Sync changes
brv curate "vX.Y.Z: <summary>" --files AGENTS.md README.md
```

---

## Anti-Patterns

| Don't | Do |
|-------|-----|
| Update code without AGENTS.md | Sync immediately |
| README version drift | Match AGENTS.md version |
| "TODO: update docs later" | Sync NOW |
| Keep 50+ lessons in AGENTS.md | Trim to 15, archive rest |
| Skip topic pre-read | READ lessons before working |
| Skip `brv curate` | Run before session end |
| Leave obsolete directories | Check ADRs, delete cruft |
