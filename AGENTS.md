# Protocol OMNI (v16.4.16)

> **Last Updated**: 2026-01-28 | **Phase**: STABLE | **Status**: R1-0528 PRODUCTION + PERF TUNING

This is a **routing document**. Details live in `docs/`. Use The Map below.

---

## Status

| Item | Value |
|------|-------|
| **Phase** | STABLE - R1-0528 Production |
| **Version** | v16.4.16 |
| **Production** | **DeepSeek-R1-0528 Q4_K_M** @ port 8000 (Iron Lung) ✅ |
| **Baseline** | **11.35 tok/s** (R1-0528 post-optimization) — +1.3% from 11.20 stock |
| **Disk** | **37% used (2.2TB free)** — cleaned 2026-01-28 |
| **Backup** | DeepSeek-R1 Q4_K_M (377GB) — original Oracle |
| **llama.cpp** | Build b7848 (`68ac3acb4`) with MLA + V-less cache + `--cache-type-k q4_1` |
| **SGLang** | **BLOCKED** (F-022) - 642GB > 584GB addressable |
| **KTransformers** | **DEFERRED** (F-027) - Future pursuit when ROI improves |
| **Memory Layer** | **TESTED** — `openmemory-py 1.3.2` (add/search/delete verified) |
| **Skill Protocol** | **ACTIVE** - Agents must check `skills/` before acting. |
| **Sentinel Audit** | 2026-01-28 - 7 upgrades: P0 (llama.cpp, MCP Apps), P1 (Scout), P2 (BitNet, Qwen3-Omni), P3 (Moltbot, NVIDIA 590.x) |
| **Health Checks** | 12/14 containers healthy |
| **Redfish** | `192.168.3.202` - Use for remote reboot |

---

## Lessons Learned (Phase 5-6)

- **2026-01-28 Performance Baseline**: Captured benchmark after session optimizations: 11.35 tok/s gen (+1.3% from 11.20 baseline), 23.14 tok/s prompt eval. CPU governor powersave→performance, GPU clocks locked 2100 MHz min. Created `benchmarks/` with scripts + systemd persistence. BIOS tuning pending (PBO/CO/FCLK).
- **2026-01-28 Redfish Limitation**: AMI Redfish on ASUS WRX90 exposes 1298 CBS attributes but ASUS-specific menus (AI Tweaker, ASUS OC) may not be visible. Memory timing controls all "Auto" — shown values may be SPD/trained, not overrides. Verify via BMC web UI or BIOS directly before assuming state.
- **2026-01-28 RAM PMIC Lock**: SK Hynix HMCGY4MHBRB489N RDIMM has voltage locked at 1.1V (Min=Max=Configured). No EXPO profile. Running 6000 MT/s vs rated 6400 MT/s. Timing-only optimization possible, no voltage scaling.
- **2026-01-28 Sentinel Integration Plan**: Created `docs/plans/2026-01-28-sentinel-audit-integration.md`. Mapped 7 upgrades: llama.cpp b7857 (P0), MCP Apps (P0), Llama 4 Scout (P1), BitNet (P2), Qwen3-Omni (P2), Moltbot (P3), NVIDIA 590.x (P3).
- **2026-01-28 R1-0528 Production**: Initial stock benchmark 11.20 tok/s (before session optimizations). Promoted for improved reasoning.
- **2026-01-28 Disk Cleanup**: Deleted V3.2 BF16/DQ3 (940GB), R1 HF (642GB), broken cpu-int8 (11GB). Freed 1.6TB → 37% disk.
- **2026-01-28 Kimi K2.5 Audit**: WATCH verdict — text-only GGUF at `AesSedai/Kimi-K2.5` (~556GB Q4_X), vision BLOCKED (Issue #19127).
- **2026-01-28 R1-0528 Q6_K OOM**: 514GB > 377GB RAM. Switched to Q4_K_M (409GB fits with swap).
- **2026-01-28 OpenMemory SDK**: `openmemory-py 1.3.2` TESTED — add/search/delete work. Py 3.14 Pydantic warning (non-blocking).
- **2026-01-28 INT8 Deleted**: Freed 642GB `/nvme/models/deepseek-r1-int8/` — confirmed unusable per F-022.
- **2026-01-27 KV Quant**: Added `--cache-type-k q4_1` for additional 7.3% speedup. R1 baseline: 11.35 tok/s (+9.7% from 10.35).
- **2026-01-27 MLA Upgrade**: llama.cpp upgraded to b7848 (`68ac3acb4`). PR #19057 + #19067 merged. 10.60 tok/s achieved (+2.4%).
- **2026-01-27 F-006 Mem0**: Docker image STILL arm64 only despite "resolved" issue. Pivoted to OpenMemory (CaviraOSS).
- **2026-01-27 Decision (Historical)**: 10.35 tok/s → 11.35 tok/s (R1). R1-0528 promoted at 11.20 tok/s stock; later optimized to 11.35 (2026-01-28).
- **2026-01-27 KTransformers**: DEFERRED for later (F-027).
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
| **Container** | `deepseek-r1-0528` | R1-0528 production |
| **Container** | `ktransformers-sglang` | DEFERRED (F-027) |

**Monitor Commands:**
```bash
# Model inventory — runs on remote
ssh omni@100.94.47.77 "du -sh /nvme/models/*/"

# GPU status — runs on remote
ssh omni@100.94.47.77 "nvidia-smi --query-gpu=memory.used,memory.total --format=csv"

# Iron Lung health — runs locally (host curl OK; use wget/python inside containers per F-021)
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
| Assume server state | Stale/wrong info | Verify via `bash` ssh (prefer) or SSH MCP for multi-step/SFTP |
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

## Sentinel Audit 2026-01-28 Summary

**Decision (2026-01-28):** R1-0528 promoted to production. Disk cleaned (1.6TB freed).

| Finding | Status | Priority |
|---------|--------|----------|
| **R1-0528 Production** | **DEPLOYED** ✅ (11.20 tok/s) | Production |
| **Disk Cleanup** | **COMPLETE** ✅ (37% used, 2.2TB free) | Done |
| llama.cpp MLA (PR #19057) | **DEPLOYED** ✅ | Done |
| KV cache quant (`q4_1`) | **DEPLOYED** ✅ | Done |
| OpenMemory SDK | **TESTED** ✅ — add/search/delete work (Py 3.14 warning only) | Done |
| Kimi K2.5 | **WATCH** — text-only GGUF works, vision blocked | Monitor |
| KTransformers v0.5.1 | **DEFERRED** (F-027) | Future |
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
