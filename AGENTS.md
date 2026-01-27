# Protocol OMNI (v16.4.10)

> **Last Updated**: 2026-01-27 | **Phase**: STABLE | **Status**: PRODUCTION RESTORED

This is a **routing document**. Details live in `docs/`. Use The Map below.

---

## Status

| Item | Value |
|------|-------|
| **Phase** | STABLE - Post-Recovery |
| **Version** | v16.4.10 |
| **Active Op** | None — Baseline accepted |
| **Production** | **llama.cpp RUNNING** @ port 8000 (Iron Lung) ✅ |
| **Baseline** | **10.35 tok/s ACCEPTED** — Expected ceiling for asymmetric GPUs |
| **SGLang** | **BLOCKED** (F-022) - 642GB > 584GB addressable |
| **KTransformers** | **DEFERRED** (F-027) - Future pursuit when ROI improves |
| **INT8 Asset** | `/nvme/models/deepseek-r1-int8/` (642GB, unusable on this hardware) |
| **Skill Protocol** | **ACTIVE** - Agents must check `skills/` before acting. |
| **Sentinel Audit** | 2026-01-27 - Driver 580.126.09 ✅, ik_llama.cpp BLOCKED (F-024) |
| **Health Checks** | 12/14 containers healthy |
| **Redfish** | `192.168.3.202` - Use for remote reboot |

---

## Lessons Learned (Phase 5-6)

- **2026-01-27 Decision**: **10.35 tok/s baseline ACCEPTED**. KTransformers DEFERRED for later.
- **F-022**: Meituan INT8 is 642GB (NOT 350GB). SGLang loads full model before offload.
- **F-023**: KTransformers 0.4.1 GGUF path requires sched_ext → prometheus-cpp → PhotonLibOS → deep dependency chain. BLOCKED.
- **F-027**: KTransformers v0.5.1 has ABI mismatch + sched_ext chain. DEFERRED (4-8h fix, ~10-30% gain).
- **S-014**: 20 tok/s requires 2x PRO 6000 symmetric (~$12K upgrade path).
- **Redfish available**: Use `mcp_redfish_*` tools for remote BMC control instead of waiting for physical access.
- **GGUF streaming wins**: llama.cpp streams layers, never needs full model in RAM.
- **Swap non-persistent**: `/nvme/swap200g` exists but NOT in `/etc/fstab`. Re-enable after reboot with `sudo swapon /nvme/swap200g`.

---

## Infrastructure Access

| Resource | Access | Notes |
|----------|--------|-------|
| **Server** | `omni@100.94.47.77` (Tailscale) | Password: ask user |
| **Local IP** | `192.168.3.10` | Only from same LAN |
| **llama.cpp** | `http://192.168.3.10:8000` | Iron Lung API |
| **Container** | `ktransformers-sglang` | DEFERRED (F-027) — future KTransformers work |
| **Container** | `deepseek-r1` | llama.cpp production |

**Monitor Commands:**
```bash
# Download progress
ssh omni@100.94.47.77 "du -sh /nvme/models/deepseek-r1-int8/ && ls /nvme/models/deepseek-r1-int8/*.safetensors 2>/dev/null | wc -l"

# GPU status
ssh omni@100.94.47.77 "nvidia-smi --query-gpu=memory.used,memory.total --format=csv"

# Iron Lung health
curl http://192.168.3.10:8000/health
```

---

## The Skill Protocol (MANDATORY)

**AGENTS MUST READ THIS FIRST.**
Before starting ANY task, you must check the Sovereign Skill Library at `~/Protocol_Omni/skills/`.

| Trigger | Required Skill | Path |
|---------|----------------|------|
| **"Debug this error"** | **Systematic Debugging** | `skills/systematic-debugging/SKILL.md` |
| **"Update docs"** | **Sentinel Doc Sync** | `skills/sentinel-doc-sync/SKILL.md` |
| **"Create new feature"** | **TDD** | `skills/test-driven-development/SKILL.md` |
| **"I'm stuck"** | **Skill Lookup** | `skills/skill-lookup/SKILL.md` |
| **"Plan this op"** | **Writing Plans** | `skills/writing-plans/SKILL.md` |

**Directives:**
1.  **No Guessing:** If a skill exists for a task, you **MUST** follow its checklist.
2.  **No Hallucinations:** Do not invent procedures. Read the `SKILL.md` first.
3.  **Red/Green/Refactor:** All code changes require TDD verification.

### Tool-First Policy (ENFORCED)

**Before responding, verify:**
- [ ] Did I check MCPs (`mcp_*` tools) for relevant capabilities?
- [ ] Did I invoke skills (`skill` tool) when applicable?
- [ ] Did I prefer tool calls over guessing when tools could achieve better results?
- [ ] Did I run `sentinel-doc-sync` + `brv curate` before claiming "done"?

| Anti-Pattern | Consequence | Correct Behavior |
|--------------|-------------|------------------|
| "I'll sync later" | Context lost on session end | Sync NOW, not later |
| Assume server state | Stale/wrong info | SSH or MCP to verify |
| Skip verification | Broken code merged | Run lint/test/typecheck |
| Guess current date | Time-sensitive errors | Check `<verdent-env>` |

**HARD RULE:** No "done" claim without:
1. Verification commands executed
2. `sentinel-doc-sync` completed
3. `brv curate` executed

---

## Critical Directives (Concrete Bunker)

| Directive | Why | Reference |
|-----------|-----|-----------|
| **Concrete Bunker** | llama.cpp = BASELINE. SGLang + kt-kernel = UPGRADE PATH. | [Resurrection Plan](docs/plans/2026-01-26-ktransformers-full-resurrection.md) |
| **Bare Metal Build** | Docker VMM disabled = 300% perf regression. | [Lessons Learned](docs/architecture/lessons-learned.md#f-003) |
| **MCP Proxy** | All tool calls via `:8070` (Default Deny policy). | [Security](docs/security/overview.md) |
| **Sync `httpx`** | Use sync `httpx.Client` for llama.cpp. | [Lessons Learned](docs/architecture/lessons-learned.md#f-007) |
| **Health Checks** | Use `wget`/`python urllib` NOT `curl` in Docker. | [Lessons Learned](docs/architecture/lessons-learned.md#f-021) |

---

## Sentinel Audit 2026-01-27 Summary

**Decision (2026-01-27):** Baseline ACCEPTED. KTransformers pursuit DEFERRED.

| Finding | Status | Priority |
|---------|--------|----------|
| **10.35 tok/s baseline** | **ACCEPTED** ✅ | Production |
| Driver 580.95.05 → 580.126.09 | **COMPLETE** ✅ (no perf gain) | Done |
| ik_llama.cpp split mode graph | **BLOCKED** (F-024) - MoE unsupported | Done |
| NVIDIA Dynamo v0.8.1 | **NOT VIABLE** (F-025) - datacenter-only | Done |
| ExLlamaV3 | **NOT VIABLE** (F-026) - DeepSeek unsupported | Done |
| 20 tok/s config | **IDENTIFIED** (S-014) - needs 2x PRO 6000 | Info |
| KTransformers v0.5.1 | **DEFERRED** (F-027) - User decision: later | Future |
| Mem0 amd64 (F-006) | **RESURRECTED** | P3 |
| vLLM SM120 (Issue #26211) | Still BLOCKED | Monitor |

**Full Report**: `docs/architecture/lessons-learned.md`

---

## The Map (Context Index)

### Key Files Index

| File | Usage Trigger | Purpose |
|------|---------------|---------|
| `skills/` | **[READ FIRST]** | The Sovereign Capability Library. |
| `docker/omni-stack.yaml` | [READ FOR INFRA] | Service definitions. |
| `src/agent/graph.py` | [READ FOR ROUTING] | LangGraph DAG. |
| `docs/architecture/tech_stack.md` | [READ FOR VERSIONS] | Driver versions & Hardware specs. |

### Key Directories

| Path | Contents |
|------|----------|
| `/nvme/models/` | Model weights (INT8 downloading, FP8 abandoned). |
| `~/Protocol_Omni/skills/` | **Agent Capabilities (TDD, Debugging, Planning).** |
| `~/Protocol_Omni/src/` | Python source code. |

---

## Post-Session Protocol (MANDATORY)

Before declaring "done":
1.  **Execute `sentinel-doc-sync`**: Ensure `AGENTS.md` matches code.
2.  **Curate Memory**: `brv curate "<What changed>" --files <path>`
3.  **Verify**: Check `docker compose ps` for zombie containers.

---
*This is a routing document. Details live in `docs/`.*
