# Protocol OMNI (v16.4.4)

> **Last Updated**: 2026-01-26 | **Phase**: 4.5 In Progress | **Status**: INT8 DOWNLOADING (Meituan Pre-Quant)

This is a **routing document**. Details live in `docs/`. Use The Map below.

---

## Status

| Item | Value |
|------|-------|
| **Phase** | 4.5 In Progress |
| **Version** | v16.4.4 |
| **Active Op** | Downloading `meituan/DeepSeek-R1-Block-INT8` (176 files, ~350GB) |
| **Asset** | INT8 downloading → `/nvme/models/deepseek-r1-int8/` |
| **Pivot** | FP8 path ABANDONED (642GB > 377GB RAM). Using Meituan pre-quantized INT8. |
| **Skill Protocol** | **ACTIVE** - Agents must check `skills/` before acting. |
| **Production** | llama.cpp RUNNING (Iron Lung baseline) @ port 8000 |
| **Download** | Running in `ktransformers-sglang` container - log: `/tmp/int8_download.log` |

---

## Infrastructure Access

| Resource | Access | Notes |
|----------|--------|-------|
| **Server** | `omni@100.94.47.77` (Tailscale) | Password: ask user |
| **Local IP** | `192.168.3.10` | Only from same LAN |
| **llama.cpp** | `http://192.168.3.10:8000` | Iron Lung API |
| **Container** | `ktransformers-sglang` | INT8 download running here |
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

---

## Critical Directives (Concrete Bunker)

| Directive | Why | Reference |
|-----------|-----|-----------|
| **Concrete Bunker** | llama.cpp = BASELINE. SGLang + kt-kernel = UPGRADE PATH. | [Resurrection Plan](docs/plans/2026-01-26-ktransformers-full-resurrection.md) |
| **Bare Metal Build** | Docker VMM disabled = 300% perf regression. | [Lessons Learned](docs/architecture/lessons-learned.md#f-003) |
| **MCP Proxy** | All tool calls via `:8070` (Default Deny policy). | [Security](docs/security/overview.md) |
| **Sync `httpx`** | Use sync `httpx.Client` for llama.cpp. | [Lessons Learned](docs/architecture/lessons-learned.md#f-007) |

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
