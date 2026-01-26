---
name: skill-lookup
description: Allows the agent to search its own capability library (~/.verdent/skills) to solve novel problems.
---

# Skill Lookup

**When to use:**
- When facing a task you don't know how to handle.
- When the user references a specific methodology (e.g., "Use systematic debugging").
- To audit available capabilities.

## Tools
You have access to the `~/.verdent/skills` directory. 

## Workflow
1. **Search**: `ls ~/.verdent/skills` to see available categories.
2. **Read**: `cat ~/.verdent/skills/<category>/SKILL.md` to absorb the capability.
3. **Apply**: Execute the task strictly following the guidelines in the SKILL.md.

## Critical Skills Index
- **Debugging**: `systematic-debugging` (Use for all errors)
- **Planning**: `writing-plans` (Use before complex ops)
- **Safety**: `verification-before-completion` (Use before 'DONE')
