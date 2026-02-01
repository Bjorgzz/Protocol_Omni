# Protocol OMNI - Complete Project Structure

> Auto-generated index. For operational docs, see [AGENTS.md](AGENTS.md).

```
Protocol_Omni/
├── AGENTS.md                    # Routing document - START HERE
├── README.md                    # Project overview + roadmap
├── STRUCTURE.md                 # This file (complete index)
├── CONTRIBUTING.md              # Contribution guidelines
├── pyproject.toml               # Python project config
├── pytest.ini                   # Test configuration
├── openmemory.db                # Local memory store
│
├── benchmarks/                  # Performance measurement
│   ├── README.md                # Benchmark tool documentation
│   ├── benchmark-sweep.sh       # Multi-preset sweep tool
│   ├── 2026-01-28-pre-optimization/
│   │   ├── benchmark-results.txt
│   │   └── settings.txt
│   └── 2026-01-29-baseline/
│       └── bios_baseline.md
│
├── config/                      # Runtime configuration
│   ├── agent_stack.yaml         # Agent framework config
│   ├── gepa.yaml                # GEPA evolution config
│   ├── gepa-local.yaml          # Local dev overrides
│   └── mcp-allowlist.yaml       # MCP tool security policy
│
├── docker/                      # Container definitions
│   ├── README.md                # Docker usage guide
│   ├── omni-stack.yaml          # Main stack compose
│   ├── agent-framework.yaml     # Agent services
│   ├── memory-stack.yaml        # Memory layer services
│   ├── observability-stack.yaml # Phoenix + monitoring
│   ├── deepseek-r1-eagle.yaml   # DeepSeek R1 deployment
│   ├── kimi-k2-oracle.yaml      # Kimi K2.5 deployment
│   ├── minimax-failsafe.yaml    # Failsafe config
│   ├── phoenix-sidecar.yaml     # Phoenix sidecar
│   ├── datasources.yaml         # Data source config
│   ├── prometheus.yml           # Prometheus config
│   ├── env.example              # Environment template
│   ├── server_mem0.py           # Mem0 server shim
│   ├── Dockerfile.blackwell     # SM120 native build
│   ├── Dockerfile.host          # Host tools
│   ├── Dockerfile.ktransformers-lazarus  # KT resurrection
│   ├── Dockerfile.mem0          # Memory layer
│   ├── Dockerfile.trt-sandbox   # TensorRT sandbox
│   └── _archive/                # Deprecated compose files
│       ├── Dockerfile.bleeding-edge
│       └── glm-executor.yaml
│
├── docs/                        # Documentation root
│   ├── README.md                # Docs index
│   │
│   ├── adr/                     # Architecture Decision Records
│   │   ├── README.md            # ADR index
│   │   ├── _template.md         # ADR template
│   │   ├── 0001-use-llamacpp-as-baseline.md
│   │   ├── 0002-use-docker-compose.md
│   │   ├── 0003-use-cpu-executor-for-coding.md  # Superseded
│   │   ├── 0004-use-phoenix-for-observability.md
│   │   └── 0005-use-gguf-weights-format.md
│   │
│   ├── api/                     # API documentation
│   │   └── README.md
│   │
│   ├── architecture/            # System architecture
│   │   ├── overview.md          # Architecture overview
│   │   ├── lessons-learned.md   # CRITICAL: Findings archive
│   │   ├── tech_stack.md        # Hardware/software versions
│   │   ├── concrete-bunker-doctrine.md
│   │   ├── ktransformers-evaluation.md
│   │   ├── memory-systems.md
│   │   ├── phase2-ik-llama-evaluation.md
│   │   ├── phase4-sovereign-cognition.md
│   │   └── zone-security.md
│   │
│   ├── deployment/              # Deployment guides
│   │   ├── quickstart.md
│   │   ├── bare-metal.md
│   │   ├── k3s-production.md
│   │   └── production-v15.md
│   │
│   ├── development/             # Dev setup
│   │   └── setup.md
│   │
│   ├── images/                  # Documentation images
│   │
│   ├── operations/              # Operational runbooks
│   │   ├── commands.md          # Common commands
│   │   ├── monitoring.md        # Monitoring guide
│   │   ├── troubleshooting.md   # Troubleshooting guide
│   │   ├── verification_procedures.md
│   │   ├── linux-kernel-tuning-ai-inference.md
│   │   ├── linux-tuning-quick-reference.md
│   │   └── 2026-01-30-memory-bandwidth-optimization-6400mhz.md
│   │
│   ├── plans/                   # Operational plans
│   │   ├── 2026-01-29-operation-velocity-extreme-ai.md
│   │   ├── 2026-01-29-operation-velocity-v3-nuclear.md
│   │   ├── 2026-01-30-operation-velocity-v4-ultrathink.md
│   │   └── archive/             # Completed/superseded plans
│   │       ├── 2026-01-25-operation-defrag.md
│   │       ├── 2026-01-25-operation-lazarus.md
│   │       ├── 2026-01-26-ktransformers-full-resurrection.md
│   │       ├── 2026-01-28-sentinel-audit-integration.md
│   │       ├── 2026-01-29-extreme-overclocking.md
│   │       └── 2026-01-29-performance-tuning.md
│   │
│   ├── prompts/                 # System prompts
│   │   └── user-rule-enforcement-addon.md
│   │
│   ├── research/                # Research documents
│   │   ├── 2026-01-30-dual-gpu-architecture-analysis.md
│   │   ├── 2026-01-30-pcie-gen5-ram-optimization-plan.md
│   │   ├── 2026-01-30-ultrathink-system-audit.md
│   │   ├── 2026-01-30-zen5-tr-9995wx-ai-bios-optimization.md
│   │   └── 2026-01-31-dual-gpu-optimization-deep-research.md
│   │
│   ├── security/                # Security documentation
│   │   └── overview.md
│   │
│   └── roadmap_phase_4_5.md     # Phase 4.5 roadmap
│
├── prompts/                     # Legacy prompt storage
│   └── _archive/
│       ├── glm-system.txt
│       ├── k2-system.txt
│       ├── letta-retrieval.txt
│       └── v32-system.txt
│
├── scripts/                     # Operational scripts
│   ├── benchmark_dragrace.py    # Benchmark comparison
│   ├── build-metal-container.sh # Container build
│   ├── check_gpu.sh             # GPU verification
│   ├── compare-benchmarks.sh    # Benchmark diff
│   ├── delete_keys.sh           # Key cleanup
│   ├── disable_sb.sh            # SecureBoot disable
│   ├── gpu_oc_extreme.sh        # GPU overclocking
│   ├── index_code.py            # Code indexing
│   ├── memgraph-schema.cypher   # Graph DB schema
│   ├── run-benchmark.sh         # Benchmark runner
│   ├── stress_test_ai.sh        # AI stress test
│   ├── stress_test_extreme.sh   # Extreme stress test
│   ├── tune-ai-inference.sh     # AI tuning
│   ├── verify-ai-tuning.sh      # Tuning verification
│   ├── persistence/             # Systemd services
│   │   ├── cpu-perf.service
│   │   └── gpu-perf.service
│   ├── _archive/                # Deprecated scripts
│   ├── _archive_deprecated/     # Fully deprecated
│   └── _archive_proxmox/        # Proxmox-specific
│
├── skills/                      # Sovereign Skill Library
│   ├── brainstorming/
│   │   └── SKILL.md
│   ├── dispatching-parallel-agents/
│   │   └── SKILL.md
│   ├── error-detective/
│   │   └── SKILL.md
│   ├── executing-plans/
│   │   └── SKILL.md
│   ├── finishing-a-development-branch/
│   │   └── SKILL.md
│   ├── kubernetes-specialist/
│   │   └── SKILL.md
│   ├── llm-architect/
│   │   └── SKILL.md
│   ├── performance-engineer/
│   │   └── SKILL.md
│   ├── receiving-code-review/
│   │   └── SKILL.md
│   ├── requesting-code-review/
│   │   ├── SKILL.md
│   │   └── code-reviewer.md
│   ├── sentinel-audit/
│   │   └── SKILL.md
│   ├── sentinel-doc-sync/
│   │   └── SKILL.md
│   ├── skill-lookup/
│   │   └── SKILL.md
│   ├── sre-engineer/
│   │   └── SKILL.md
│   ├── subagent-driven-development/
│   │   ├── SKILL.md
│   │   ├── code-quality-reviewer-prompt.md
│   │   ├── implementer-prompt.md
│   │   └── spec-reviewer-prompt.md
│   ├── summarizing-project-state/
│   │   └── SKILL.md
│   ├── systematic-debugging/
│   │   ├── SKILL.md
│   │   ├── CREATION-LOG.md
│   │   ├── condition-based-waiting.md
│   │   ├── condition-based-waiting-example.ts
│   │   ├── defense-in-depth.md
│   │   ├── find-polluter.sh
│   │   ├── root-cause-tracing.md
│   │   └── test-*.md              # Test pressure docs
│   ├── test-driven-development/
│   │   ├── SKILL.md
│   │   └── testing-anti-patterns.md
│   ├── using-git-worktrees/
│   │   └── SKILL.md
│   ├── using-superpowers/
│   │   └── SKILL.md
│   ├── verification-before-completion/
│   │   └── SKILL.md
│   ├── writing-plans/
│   │   └── SKILL.md
│   ├── writing-skills/
│   │   ├── SKILL.md
│   │   ├── anthropic-best-practices.md
│   │   ├── graphviz-conventions.dot
│   │   ├── persuasion-principles.md
│   │   ├── render-graphs.js
│   │   ├── testing-skills-with-subagents.md
│   │   └── examples/
│   │       └── CLAUDE_MD_TESTING.md
│   └── _deprecated/              # Deprecated skills
│       └── memory-sync/
│           ├── SKILL.md
│           └── DEPRECATED.md
│
├── src/                         # Source code
│   ├── README.md                # Source overview
│   │
│   ├── agent/                   # Main agent
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point
│   │   ├── graph.py             # LangGraph DAG
│   │   ├── router_legacy.py     # Legacy router
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   ├── nodes/               # Graph nodes
│   │   │   ├── __init__.py
│   │   │   ├── classification.py
│   │   │   ├── inference.py
│   │   │   ├── knowledge.py
│   │   │   ├── memory.py
│   │   │   ├── metacognition.py
│   │   │   ├── state.py
│   │   │   └── status.py
│   │   └── tools/               # Agent tools
│   │       ├── __init__.py
│   │       └── status.py
│   │
│   ├── dashboard/               # UI dashboard
│   │   └── app.py
│   │
│   ├── gepa/                    # Evolution engine
│   │   ├── __init__.py
│   │   ├── evolution.py
│   │   ├── pareto.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── knowledge/               # Knowledge graph
│   │   ├── __init__.py
│   │   └── memgraph_client.py
│   │
│   ├── mcp_proxy/               # MCP security proxy
│   │   ├── __init__.py
│   │   ├── allowlist.py
│   │   ├── audit.py
│   │   ├── gateway.py
│   │   └── Dockerfile
│   │
│   ├── memory/                  # Memory layer
│   │   ├── __init__.py
│   │   └── mem0_client.py
│   │
│   └── metacognition/           # Self-reflection
│       ├── __init__.py
│       ├── engine.py
│       ├── gates.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_classification.py
│   │   ├── test_graph.py
│   │   ├── test_mcp_allowlist.py
│   │   └── test_mem0_client.py
│   └── integration/
│       ├── __init__.py
│       └── test_remote_services.py
│
├── tools/                       # External tools
│   └── bios/                    # BIOS manipulation
│       ├── wrx90_ifr_full.json  # IFR database (33k lines)
│       ├── wrx90_ai_settings_analysis.md
│       ├── export_settings.nsh
│       ├── extreme_settings.nsh
│       └── nuclear_settings.nsh
│
├── .github/                     # GitHub config
│   └── ISSUE_TEMPLATE/
│       ├── config.yml
│       ├── blocker.yml
│       ├── enhancement.yml
│       └── investigation.yml
│
├── .verdent/                    # Verdent agent state
│   └── plans/                   # Execution plans
│
├── .clinerules/                 # Cline rules
│   ├── agent-context.md
│   └── agent-context-engineering.md
│
├── .kilocode/                   # Kilocode config
│   └── worktrees/
│
├── .streamlit/                  # Streamlit config
│   └── secrets.toml
│
└── .vscode/                     # VSCode settings
    └── settings.json
```

## Quick Navigation

| Need | Go To |
|------|-------|
| **Start here** | [AGENTS.md](AGENTS.md) |
| **Project overview** | [README.md](README.md) |
| **Lessons learned** | [docs/architecture/lessons-learned.md](docs/architecture/lessons-learned.md) |
| **Hardware specs** | [docs/architecture/tech_stack.md](docs/architecture/tech_stack.md) |
| **Skills library** | [skills/](skills/) |
| **Benchmark tool** | [benchmarks/](benchmarks/) |
| **Architecture decisions** | [docs/adr/](docs/adr/) |

---
*Generated: 2026-02-01*
