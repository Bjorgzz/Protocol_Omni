# Protocol OMNI: Tech Stack Reference

> **Last Updated**: 2026-01-27  
> **Version**: v16.4.12

Hardware specifications, software versions, and stack decisions for Protocol OMNI infrastructure.

---

## Hardware Substrate

### Target Host

| Property | Value |
|----------|-------|
| **IP** | `192.168.3.10` |
| **Hostname** | `omni-prime` |
| **User** | `omni` |
| **OS** | Ubuntu 24.04 LTS (Kernel 6.8.0+) |

### BMC Access

| Property | Value |
|----------|-------|
| **IP** | `192.168.3.202` |
| **User** | `admin` |
| **Redfish API** | `https://192.168.3.202/redfish/v1/` |

### Compute

| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Threadripper 9995WX (96 Cores, Zen5 AVX-512) |
| **RAM** | 384GB DDR5-6400 (ECC), **NPS=1 (Unified NUMA)** |
| **GPU 0** | RTX PRO 6000 Blackwell (96GB, SM 12.0) @ `f1:00.0` (Max 600W) |
| **GPU 0 UUID** | `GPU-f4f210c1-5a52-7267-979e-fe922961190a` |
| **GPU 1** | RTX 5090 (32GB, SM 12.0) @ `11:00.0` (Max 800W) |
| **GPU 1 UUID** | `GPU-bfbb9aa1-3d36-b47b-988f-5752cfc54601` |
| **Storage** | 2× 4TB NVMe Gen5 |

### BIOS Configuration

> **MANDATORY**: NPS1 (Unified NUMA) is non-negotiable for all bare-metal rebuilds.

| Setting | Value | Why |
|---------|-------|-----|
| `CbsDfCmnDramNpsSHP` | `NPS1` | Eliminates cross-die memory latency for 671B inference |
| Cold boot required | Yes | Warm reboot may hang after BIOS change |
| Backup | `~/bios_backup_nps4_baseline.json` | md5: `86f43f927ad3af324f913ac9ec3a88a2` |

---

## Software Stack

### Runtime

| Component | Version | Notes |
|-----------|---------|-------|
| Host OS | Ubuntu 24.04 LTS | Kernel 6.8.0+ |
| Docker CE | 29.x | Zone A runtime |
| gVisor (runsc) | Latest | Zone B runtime (no GPU) |
| Orchestration | Docker Compose / k3s | Compose for dev, k3s for prod |

### NVIDIA Stack

| Component | Version | Notes |
|-----------|---------|-------|
| NVIDIA Driver | 580.x | Open GPU Kernel Modules |
| CUDA | 13.x | SM 12.0 support |
| PyTorch | 2.11.0+cu130 | CUDA 13 build |

### Inference Engine

| Component | Version | Configuration |
|-----------|---------|---------------|
| llama.cpp | `68ac3acb4` (b7848) | MLA optimized, `BLACKWELL_NATIVE_FP4=1` |
| Docker Image | `omni/llama-server:sm120-cuda13` | Built via `build-metal-container.sh` |
| GPU Layers | 15 | ~96GB (82GB Blackwell + 15GB 5090) |
| Tensor Split | `75,25` | Asymmetric GPU allocation |
| Flash Attention | Enabled | `--flash-attn` |
| KV Cache | q4_1 quantized | `--cache-type-k q4_1` (+7.3% speedup) |
| Context Slots | 4 @ 8192 | 32K total context |

### Models

| Model | Quantization | Size | Role | Status |
|-------|--------------|------|------|--------|
| DeepSeek-V3.2 | Q3_K_M | ~281GB | Primary Oracle | **LIVE** |
| Qwen2.5-Coder-7B | Q4_K_M | ~6.4GB | CPU Executor | **LIVE** |
| MiniMax M2.1 | — | — | Cold Storage | Profile: emergency |

---

## Stack Assessment (2026-01-27 Update)

> **Note**: Updated 2026-01-27 to reflect F-006 pivot from Mem0 to OpenMemory.

| Layer | Choice | Alternatives Evaluated | Verdict |
|-------|--------|------------------------|---------|
| **Orchestration** | LangGraph v1.0.6 | CrewAI, AutoGen (deprecated), PydanticAI, Aegra | **OPTIMAL** |
| **Inference** | llama.cpp sm_120 | vLLM, SGLang, TensorRT-LLM | **ONLY OPTION** |
| **Memory** | OpenMemory (CaviraOSS) | Mem0 (F-006 BLOCKED), Letta, Zep (deprecated) | **SELECTED** — local-first, SQLite |
| **Observability** | Phoenix OTEL 0.14.0 | Langfuse, OpenLLMetry, LangSmith | **UPGRADED** |
| **Model** | DeepSeek-V3.2 671B | GLM-4.7, Kimi K2, MiniMax-M2.1 | **#2 OPEN** |

### Key Finding: AutoGen Deprecation

> Microsoft AutoGen is entering **maintenance mode** (bug fixes only) as of late 2025.
> AutoGen and Semantic Kernel are merging into "Microsoft Agent Framework" targeting Q1 2026 GA.

### Alternative Engines Status

| Engine | SM120 Support | Status | Blocker |
|--------|--------------|--------|---------|
| llama.cpp | Working | **KEEP** | None |
| vLLM | v0.12.0+ | BLOCKED | FP8 GEMM kernel fails (Issue #26211) |
| SGLang | In Progress | BLOCKED | RMSNorm kernel issues (#7227, #9542) |
| KTransformers | Broken | BLOCKED | AMD BLIS INT4 kernels missing |
| **NVIDIA Dynamo** | Unknown | EVALUATE | New framework (Jan 2026) |

---

## Performance Baselines

### DeepSeek-V3.2 (v16.2.2 - NPS1 Optimized)

| Metric | NPS4 (Before) | NPS1 (After) | Improvement |
|--------|---------------|--------------|-------------|
| Generation | 5.2 tok/s | **10.9 tok/s** | 2.1x |
| Prompt Eval | 10.5 tok/s | **20.5 tok/s** | 1.95x |

### Qwen2.5-Coder-7B (CPU Executor)

| Metric | Value |
|--------|-------|
| Threads | 192 (AVX-512) |
| Speed | 16.39 tok/s |

---

## Community Resources

| Community | Link | Relevance |
|-----------|------|-----------|
| r/LocalLLaMA Discord | `discord.gg/rC922KfEwj` | llama.cpp, Blackwell, self-hosted |
| LangChain Forum | `forum.langchain.com` | `#self-hosted` for LangGraph |
| Aegra Project | `github.com/ibbybuilds/aegra` | Self-hosted LangGraph Platform |

---

## Upgrade Opportunities

| Priority | Action | Status |
|----------|--------|--------|
| P1 | Phoenix 0.1.0 → 0.14.0 | ✅ Complete (v16.3.0) |
| P2 | llama.cpp MXFP4 benchmark | 🔄 In Progress |
| P2 | NVIDIA Dynamo sandbox test | Pending |
| P3 | Monitor vLLM SM120 progress | Watching |
| P4 | Evaluate GLM-4.7 GGUF release | Watching |
