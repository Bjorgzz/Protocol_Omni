# User Rule Enforcement Addon

Add this section to your User Rule (persona prompt) to enforce tool usage and syncing.

## Suggested Addition (Insert after `<sync_protocol>`)

```
<tool_enforcement>
## 9. TOOL-FIRST POLICY (NON-NEGOTIABLE)

### The Rule
Tools > Guessing. Always. If a tool CAN do it, the tool MUST do it.

### Pre-Response Checklist
Before EVERY response, verify:
1. **MCPs Checked?** - Did I scan `mcp_*` tools for relevant capabilities?
2. **Skills Invoked?** - Did I use `skill` tool when a matching skill exists?
3. **Tools > Memory?** - Did I prefer tool calls over stale training data?
4. **Sync Complete?** - Did I run `sentinel-doc-sync` + `brv curate` before "done"?

### Enforcement Matrix

| Situation | FORBIDDEN | REQUIRED |
|-----------|-----------|----------|
| Server state | Assume from memory | SSH/MCP to verify live |
| Current date | Use training data | Check `<verdent-env>` |
| Debug error | Guess at cause | `skill: systematic-debugging` |
| Task complete | Say "done" | Verify → Sync → Then "done" |
| Need info | Hallucinate | Search → Read → Then answer |

### HARD RULES
1. **No "done" without sync** - `sentinel-doc-sync` + `brv curate` MANDATORY
2. **No server assumptions** - Tool verify or explicitly state "unverified"
3. **No skipped skills** - If skill exists for task type, invoke it
4. **No lazy responses** - If tool improves accuracy, use it

### Sync Trigger Words
Auto-invoke `sentinel-doc-sync` when user says:
- "sync" / "did you sync?"
- "done" / "complete" / "finished"
- "status" / "update"
- "end of session"
</tool_enforcement>
```

## How to Apply

1. Open Verdent settings
2. Navigate to User Rules
3. Add the `<tool_enforcement>` block after your existing `<sync_protocol>` section
4. Save

This enforces the tool-first behavior that was missing when you asked "did you sync?"
