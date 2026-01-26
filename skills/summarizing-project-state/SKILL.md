---
name: summarizing-project-state
description: Use when ending a session, onboarding new agents, or when context window is filling up - produces holistic status report including active phases, abandoned paths, and remaining tasks
---

# Summarizing Project State

## Overview

Produce a comprehensive project status report by scanning core documentation files AND ByteRover memory. The summary captures current phase, abandoned experiments, working configurations, and remaining tasks.

## When to Use

- Session ending or handoff to another agent
- Context window approaching limit
- Before major architectural decisions
- Onboarding new agents to the project
- After completing a major phase

## Core Pattern

### Step 0: Query ByteRover (MANDATORY FIRST)

Before reading files, retrieve architectural context from ByteRover:

```bash
# Check current context tree status
brv status

# Query for abandoned paths and pivots
brv query "What engines or approaches were abandoned and why?"

# Query for current architecture
brv query "What is the current system architecture and deployment status?"
```

**Key Context Paths:**
- `.brv/context-tree/structure/architecture/` - Architecture decisions
- `.brv/context-tree/compliance/constraints/` - Blockers and constraints
- `.brv/context-tree/structure/operations/` - Deployment status

### Step 1: Scan Required Sources

After ByteRover, scan these files:

1. **AGENTS.md** - Current operational doctrine and version
2. **docs/architecture/lessons-learned.md** - Failure registry and pivots
3. **docs/architecture/phase4-sovereign-cognition.md** - Current phase details (if exists)
4. **docker/omni-stack.yaml** - Active service configuration

### Step 2: Synthesize Report

Merge ByteRover context with file sources:

```markdown
## Project Status Report (v{VERSION})

### Current Phase
- Phase name and status (from AGENTS.md + brv operations/)
- Key active services (from omni-stack.yaml)

### Abandoned Paths (ByteRover + lessons-learned.md)
- Engine/approach that failed
- Why it failed (1-line)
- ByteRover context path for details

### Green Zone (Working)
- Verified working configurations
- Performance baselines (from brv hardware/)

### Remaining Tasks
- Outstanding work items
- Blockers if any (from brv constraints/)
```

## Quick Reference

| Section | Source | Key Fields |
|---------|--------|------------|
| Version | AGENTS.md | Line 3 header |
| Phases | AGENTS.md Section 4 | Roadmap table |
| Abandoned Paths | `brv query "abandoned"` + lessons-learned.md | Failure Registry |
| Pivots | `.brv/context-tree/structure/architecture/` | ktransformers_evaluation_conclusion.md |
| Constraints | `.brv/context-tree/compliance/constraints/` | sentinel_audit, amd_blis |
| Deployment | `.brv/context-tree/structure/operations/` | v16_2_4_deployment_status.md |
| Services | omni-stack.yaml | services: block |

## Implementation

```python
def summarize_project_state():
    # Step 0: ByteRover context (MANDATORY)
    brv_context = {
        "status": run("brv status"),
        "abandoned": brv_query("abandoned engines approaches"),
        "architecture": brv_query("current system architecture"),
    }
    
    # Step 1: File sources
    sources = [
        "AGENTS.md",
        "docs/architecture/lessons-learned.md", 
        "docker/omni-stack.yaml"
    ]
    
    # Step 2: Synthesize
    report = {
        "version": extract_version(sources[0]),
        "phases": extract_phase_table(sources[0]),
        "failures": merge(brv_context["abandoned"], extract_failure_registry(sources[1])),
        "pivots": brv_context["architecture"],
        "services": extract_service_status(sources[2])
    }
    
    return format_status_report(report)
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping ByteRover | Missing curated architectural context - always query first |
| Missing lessons-learned.md | Creates incomplete report - always check |
| Outdated phase status | Cross-reference with actual container state |
| Ignoring pivots | Pivots explain WHY current state exists |
| Not reading brv constraints/ | Missing blockers like AMD BLIS INT4 kernel gap |
