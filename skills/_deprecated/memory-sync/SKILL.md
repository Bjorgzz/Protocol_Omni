---
name: memory-sync
description: Use when ending a session, completing a major task, reaching context limits, or before declaring work complete - mandatory shutdown protocol to persist state to ByteRover
---

# Memory Sync

## Overview

A shutdown protocol that persists agent state before session termination. Ensures no context is lost between sessions.

## When to Use

- Before ending any session
- After completing a significant task
- When context limit is approaching (~15+ messages)
- Before declaring "done" or "complete"
- Before asking "What's next?"

## Execution Protocol

**MANDATORY: Execute these steps in sequence.**

```
┌─────────────────────────────────────────┐
│  1. CURATE STATE                        │
│     brv curate "<summary>" --files <path>│
├─────────────────────────────────────────┤
│  2. UPDATE STATUS (if needed)           │
│     Edit AGENTS.md Status section       │
├─────────────────────────────────────────┤
│  3. SUMMARIZE (if context heavy)        │
│     Use summarizing-project-state skill │
└─────────────────────────────────────────┘
```

### Step Details

| Step | Action | Purpose |
|------|--------|---------|
| 1 | `brv curate "<What changed>" --files <path>` | Captures discoveries to ByteRover |
| 2 | Edit AGENTS.md Status section | Update phase/alerts if changed |
| 3 | Invoke `summarizing-project-state` | Generate handoff summary (optional, for heavy context) |

## Quick Reference

```bash
# Always do this
brv curate "v16.3.x: <What changed>" --files <relevant-file>

# If status changed, manually update AGENTS.md:
# - Status table at top
# - Phase / Active Operation / Alerts
```

## Trigger Output

When invoking this protocol, output:

```
Architecting Memory... [Syncing ByteRover]
```

Then execute the steps.

## Red Flags - STOP and Sync

- About to say "Task complete"
- About to ask "What's next?"
- Context feels heavy (15+ messages)
- Major architectural decision made
- New pattern or constraint established

**All of these mean: Run memory-sync first.**

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping sync before "done" | Never declare complete without syncing |
| Forgetting to curate discoveries | Every new pattern → `brv curate` |
| Not updating AGENTS.md Status | Check if phase/alerts changed |

## Integration

**Related Skills:**
- `summarizing-project-state` - Use for detailed handoff when context is heavy
- `verification-before-completion` - Run before claiming work complete
