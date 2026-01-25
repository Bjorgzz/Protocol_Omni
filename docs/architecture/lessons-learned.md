# Protocol OMNI: Lessons Learned Registry

> **Purpose**: Chronicle of failures, pivots, and hard-won knowledge for AI agent training  
> **Last Updated**: 2026-01-25  
> **Versions Covered**: v13.0 → v16.3.2

This document captures architectural decisions, failed experiments, and pivots to prevent agents from repeating mistakes.

---

## Quick Reference: What NOT To Do

| Anti-Pattern | Why It Failed | Correct Approach |
|--------------|---------------|------------------|
| KTransformers on Blackwell | ~~sm_120 kernels missing~~ **LAZARUS** | Re-evaluate with PyTorch 2.8+ Nightly (cu128) |
| ik_llama.cpp for asymmetric GPUs | NCCL overhead on pipeline parallelism | Standard llama.cpp with `--tensor-split` |
| vLLM on SM120 | FP8 GEMM kernel fails | Wait for v0.13+ or use llama.cpp |
| SGLang on Blackwell | RMSNorm kernel issues | Wait for upstream fix |
| Disable CUDA VMM in Docker | 300% performance regression | Build on bare metal, package into container |
| gVisor for GPU workloads | No GPU passthrough | Standard Docker for Zone A |
| 4-model Cognitive Trinity | VRAM oversubscription | 2-model architecture (Oracle + Executor) |
| Mem0 Docker deployment | No linux/amd64 image | Build from source or use OpenMemory MCP |
| httpx.AsyncClient for llama.cpp | HTTP/2 negotiation 400 errors | Sync `httpx.Client` + `asyncio.to_thread()` |
| Undeclared LangGraph state fields | Fields silently dropped | Always declare in TypedDict schema |
| Memgraph on Zen 5 (9995WX) | AVX512 GPF in libc | Add `GLIBC_TUNABLES=glibc.cpu.hwcaps=-AVX512F,-AVX512VL,-AVX512BW,-AVX512CD,-AVX512DQ` |
| MXFP4 "Experimental" models | `deepseek3_2` arch unsupported | Verify `general.architecture` in GGUF before download |

---

## Failure Registry

### F-001: KTransformers SM120 Incompatibility → RESURRECTION CANDIDATE

**Date**: 2026-01-19 | **Updated**: 2026-01-25  
**Severity**: ~~BLOCKING~~ **RESURRECTION CANDIDATE**  
**Document**: [KTransformers Evaluation](ktransformers-evaluation.md)

**Symptoms**:
```
RuntimeError: CUDA error: no kernel image is available for execution on device
```

**Root Cause**: KTransformers uses pre-compiled CUDA kernels (sm_75/86/89). Blackwell requires sm_120.

**Attempted Fixes**:
| Attempt | Result |
|---------|--------|
| Pull newer image | Disk full (100% partition) |
| Build from source | PyTorch lacks sm_120 |
| Use vLLM instead | MoE not supported |
| Use SGLang | Same kernel gap |

**Resolution**: Adopted llama.cpp with explicit sm_120 compilation.

**2026-01-25 Update (Operation Lazarus):**  
PyTorch 2.8+ Nightly (cu128) verified to support SM120. KTransformers re-evaluation pending.  
**Verification:** `torch.cuda.get_arch_list()` must show `sm_120`.  
**Plan:** [Operation Lazarus](../plans/2026-01-25-operation-lazarus.md)

**Lesson**: Pre-compiled inference engines are fragile on new silicon. Prefer source-compiled engines (llama.cpp) for bleeding-edge GPUs.

---

### F-002: ik_llama.cpp Performance Regression

**Date**: 2026-01-22  
**Severity**: MAJOR  
**Document**: [Phase 2 ik_llama Evaluation](phase2-ik-llama-evaluation.md)

**Symptoms**: 40% slower than baseline (6.1 tok/s vs 10.75 tok/s)

**Root Cause**: ik_llama.cpp optimizations target **symmetric tensor parallelism**. Our setup uses **asymmetric pipeline parallelism** (96GB + 32GB GPUs).

**Key Insight**:
> "Tensor Parallelism requires 50/50 split (matrix operations). Our GPUs: 96GB vs 32GB (3:1 asymmetry). Pipeline Parallelism (bucket filling) is the only viable option."

**Resolution**: Reverted to standard llama.cpp with `--tensor-split 75,25`.

**Lesson**: Multi-GPU optimizations assume identical hardware. Asymmetric clusters need different strategies (pipeline parallelism).

---

### F-003: CUDA VMM Disabled in Docker Build

**Date**: 2026-01-22  
**Severity**: CRITICAL  
**Document**: [AGENTS.md v16.1.4 - Sentinel Audit 2026-01 Verdict](../../AGENTS.md#sentinel-audit-2026-01-verdict-section-3)

**Symptoms**: 300% performance regression (10.75 tok/s → 3.68 tok/s)

**Root Cause**: Disabling `GGML_CUDA_NO_VMM=ON` to fix Docker linking errors removes CUDA Virtual Memory Management, which is required for efficient PCIe tensor transfers between GPUs.

**The Wrong Fix**:
```cmake
-DGGML_CUDA_NO_VMM=ON  # NEVER DO THIS
```

**Resolution**: Build llama.cpp on bare metal (with host NVIDIA drivers), then package binary into container.

**Correct Build Path**:
```bash
# On bare metal host (NOT in Docker)
cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DGGML_NATIVE=ON \
  -DGGML_AVX512=ON
cmake --build build -j $(nproc)

# Package into container (preserves VMM)
./scripts/build-metal-container.sh
```

**Lesson**: Docker CUDA builds have limitations. For maximum performance, compile on bare metal and containerize the binary.

---

### F-004: gVisor GPU Isolation Failure

**Date**: 2026-01-18  
**Severity**: BLOCKING  
**Document**: [Zone Security](zone-security.md)

**Symptoms**: GPU not visible inside gVisor containers

**Root Cause**: gVisor (runsc) cannot pass through NVIDIA GPUs. The `/dev/nvidia*` devices require direct kernel access.

**Resolution**: Standard Docker runtime for Zone A (GPU workloads). gVisor reserved for Zone B (untrusted code execution).

**Lesson**: Hardware passthrough (GPU, RDMA) is incompatible with most sandbox runtimes.

---

### F-005: 4-Model Cognitive Trinity VRAM Overrun

**Date**: 2026-01-19  
**Severity**: MAJOR

**Original Plan**:
| Model | Role | VRAM Required |
|-------|------|---------------|
| DeepSeek-V3.2 | Oracle | ~117GB |
| GLM-4.7 | Executor | ~20GB |
| MiniMax M2.1 | Failsafe | ~30GB |
| Kimi K2 | Tool Heavy | API |

**Total VRAM Required**: ~167GB  
**Total VRAM Available**: 128GB (96GB + 32GB)

**Resolution**: Simplified to 2-model architecture:
- DeepSeek-V3.2 (GPU Oracle)
- Qwen2.5-Coder-7B (CPU Executor, 192 AVX-512 threads)

**Lesson**: VRAM budgets must be calculated with overhead. Leave 10-15% headroom for KV cache growth.

---

### F-006: ByteRover Node.js Version Incompatibility

**Date**: 2026-01-22  
**Severity**: MINOR

**Symptoms**: `brv` CLI crashes on startup

**Root Cause**: ByteRover requires Node.js 20 or 22. System had Node.js 25.3 installed.

**Resolution**:
```bash
nvm use 22
```

**Lesson**: Pin Node.js versions for CLI tools. Use `nvm` to manage.

---

## Success Registry

> Documenting what worked prevents agents from abandoning proven solutions.

### S-001: Bare Metal Build + Container Package (10.9 tok/s NPS1)

**Date**: 2026-01-22  
**Impact**: HIGH

**What Worked**: Compiling llama.cpp on bare metal (host OS with real NVIDIA drivers), then packaging the binary into a Docker container via `docker commit`.

**Key Configuration**:
```bash
--n-gpu-layers 19
--tensor-split 75,25
--ctx-size 8192
--flash-attn
```

**Why It Worked**: Preserved CUDA VMM (Virtual Memory Management) for efficient PCIe tensor transfers between asymmetric GPUs.

---

### S-002: CPU Executor on Threadripper (16.39 tok/s)

**Date**: 2026-01-20  
**Impact**: HIGH

**What Worked**: Running Qwen2.5-Coder-7B on CPU-only mode using all 192 AVX-512 threads of the Threadripper 9995WX.

**Key Configuration**:
```yaml
CUDA_VISIBLE_DEVICES: ""  # Disable GPU
--threads 192
--n-gpu-layers 0
```

**Why It Worked**: Filled 340GB idle RAM void while keeping GPU VRAM dedicated to Oracle model.

---

### S-003: Asymmetric Tensor Split (75/25)

**Date**: 2026-01-19  
**Impact**: HIGH

**What Worked**: Using `--tensor-split 75,25` to distribute layers proportionally across 96GB Blackwell + 32GB 5090.

**Why It Worked**: Matches the 3:1 VRAM ratio. Pipeline parallelism (bucket filling) works on asymmetric hardware, unlike tensor parallelism.

---

### S-004: Internal Brain Network Isolation

**Date**: 2026-01-20  
**Impact**: MEDIUM

**What Worked**: Docker network with `internal: true` prevents Oracle from making outbound internet requests.

```yaml
networks:
  internal_brain:
    driver: bridge
    internal: true
```

**Why It Worked**: Simple, zero-overhead network isolation without gVisor complexity.

---

### S-005: NPS1 BIOS Optimization (2.1x Speedup)

**Date**: 2026-01-24  
**Impact**: CRITICAL

**What Worked**: Configuring BIOS to NPS1 (Unified NUMA) instead of NPS4 for the Threadripper 9995WX.

**Key Configuration**:
```
BIOS Setting: CbsDfCmnDramNpsSHP=NPS1
Verification: numactl --hardware → "available: 1 nodes"
```

**Performance Improvement**:
| Metric | NPS4 (Before) | NPS1 (After) | Improvement |
|--------|---------------|--------------|-------------|
| Generation | 5.2 tok/s | 10.9 tok/s | **2.1x** |
| Prompt Eval | 10.5 tok/s | 20.5 tok/s | **1.95x** |

**Why It Worked**: NPS1 eliminates cross-die memory latency penalty. DeepSeek-V3.2 671B model benefits from unified memory access patterns across all 96 cores.

**Lesson**: For large language models that span CPU RAM, unified NUMA topology outperforms partitioned. Always verify with `numactl --hardware` before benchmarking.

---

## Pivot Registry

### P-001: KTransformers → llama.cpp (Concrete Bunker Doctrine)

**Date**: 2026-01-19  
**Document**: [Concrete Bunker Doctrine](concrete-bunker-doctrine.md)

**Original State**: KTransformers for DeepSeek-V3.2 inference  
**New State**: llama.cpp with sm_120 compilation

**Trade-offs**:
| Lost | Gained |
|------|--------|
| 20+ tok/s target | 10.9 tok/s stable (NPS1) |
| Speculative decoding | Reproducible builds |
| DeepGEMM | sm_120 native support |
| 4-model routing | Simplified 2-model stack |

---

### P-002: Kubernetes → Docker Compose

**Date**: 2026-01-20

**Original State**: k3s with Talos Linux  
**New State**: Docker Compose on Ubuntu 24.04

**Reason**: Simpler debugging during hardware bringup. k3s can be reintroduced after stack stabilizes.

---

### P-003: GLM-4.7 → Qwen2.5-Coder-7B (Executor)

**Date**: 2026-01-20

**Original State**: GLM-4.7 on GPU  
**New State**: Qwen2.5-Coder-7B on CPU (192 threads)

**Reason**: Free up GPU VRAM for Oracle. Qwen achieves 16.39 tok/s on CPU with AVX-512.

---

### P-004: Langfuse → Arize Phoenix (Observability)

**Date**: 2026-01-21

**Original State**: Langfuse for tracing  
**New State**: Arize Phoenix with OTEL

**Reason**: Phoenix has native OTEL support and better GPU metric correlation.

---

## Sentinel Audit 2026-01: Engine Evaluation

**Date**: 2026-01-23  
**Document**: [AGENTS.md Section 3](../../AGENTS.md)

Comprehensive evaluation of alternative inference engines for Blackwell:

| Engine | SM120 Support | Status | Blocker |
|--------|--------------|--------|---------|
| llama.cpp | Working | **KEEP** | None |
| KTransformers | Broken | BLOCKED | PyTorch sm_120 kernels |
| ik_llama.cpp | Working | REJECTED | 40% regression on asymmetric GPUs |
| vLLM | v0.12.0+ | BLOCKED | FP8 GEMM kernel fails (Issue #26211) |
| SGLang | In Progress | BLOCKED | RMSNorm kernel issues (Issue #9542) |

**Verdict**: Retain llama.cpp. Re-evaluate alternatives in Q2 2026.

---

## Paradigm Audit 2026-01-25: Full Stack Comparison

**Date**: 2026-01-25  
**Document**: [AGENTS.md Section 3](../../AGENTS.md)

Comprehensive evaluation of alternatives across all stack layers:

| Layer | Current Choice | Top Alternative | Verdict |
|-------|---------------|-----------------|---------|
| Orchestration | LangGraph v1.0.6 | CrewAI | ✓ **OPTIMAL** - AutoGen deprecated |
| Inference | llama.cpp sm_120 | NVIDIA Dynamo | ✓ **ONLY OPTION** - Dynamo for sandbox test |
| Memory | Mem0 v1.0.2 | Letta (MemGPT) | ✓ **CURRENT** - Letta upgrade path |
| Observability | Phoenix OTEL 0.14.0 | Langfuse | ✓ **UPGRADED** |
| Model | DeepSeek-V3.2 | GLM-4.7 | ✓ **#2** - GLM-4.7 marginal leader |

**Key Discovery - AutoGen Deprecation:**
> Microsoft AutoGen is entering **maintenance mode** (bug fixes only) as of late 2025.
> AutoGen and Semantic Kernel are merging into "Microsoft Agent Framework" targeting Q1 2026 GA.
> For new projects, evaluate LangGraph or wait for Microsoft Agent Framework.

**Community Resources Identified:**
- **r/LocalLLaMA Discord** (`discord.gg/rC922KfEwj`): 600K+ members, closest match for llama.cpp + Blackwell
- **LangChain Forum** (`forum.langchain.com`): `#self-hosted` tag for LangGraph deployments
- **Aegra Project** (`github.com/ibbybuilds/aegra`): Self-hosted LangGraph Platform alternative

**NVIDIA Dynamo Opportunity:**
- Distributed inference framework for multi-node/multi-GPU environments
- Relevant for 96GB + 32GB asymmetric GPU split
- Status: Sandbox test pending

---

## For AI Agents: Before You Suggest...

### "What about vLLM?"
Read F-001. FP8 GEMM kernel fails on consumer SM120 (Issue #26211). Wait for v0.13+.

### "What about KTransformers?"
Read F-001. Pre-compiled kernels don't support sm_120. Also blocked by AMD BLIS INT4 kernels.

### "What about ik_llama.cpp for faster inference?"
Read F-002. Only beneficial for symmetric GPU clusters with NVLink. Our 96GB+32GB setup uses pipeline parallelism.

### "Why not disable VMM to fix Docker build?"
Read F-003. 300% performance regression. Build on bare metal instead.

### "Why not use gVisor for GPU isolation?"
Read F-004. gVisor cannot pass through NVIDIA devices.

### "Can we add more models?"
Read F-005. Current 2-model architecture is at VRAM limit. Adding models requires removing existing ones or using CPU.

### "Can we deploy Mem0 for persistent memory?"
Read F-006. The `mem0/mem0-api-server` Docker image lacks linux/amd64 support. Options: build from source, use OpenMemory MCP, or wait for official amd64 image.

### "What about AutoGen for agent orchestration?"
AutoGen is in **maintenance mode** as of late 2025. Microsoft is merging AutoGen with Semantic Kernel into "Microsoft Agent Framework" (Q1 2026 GA). Use LangGraph instead — it's the optimal choice for self-hosted, model-agnostic, explicit DAG control.

---

## F-006: Mem0 Docker Image Platform Incompatibility

**Date**: 2026-01-24  
**Severity**: BLOCKING  
**Component**: mem0 persistent memory layer

**Symptoms**:
```
Error response from daemon: no matching manifest for linux/amd64 in the manifest list entries
```

**Root Cause**: `mem0/mem0-api-server:latest` only publishes ARM64 images. No linux/amd64 variant exists.

**Attempted Fixes**:
| Attempt | Result |
|---------|--------|
| `docker pull mem0ai/mem0:latest` | Image does not exist |
| `docker pull mem0/mem0-api-server:latest` | No amd64 manifest |

**Resolution**: Commented out mem0 service in omni-stack.yaml. Using Qdrant directly for vector storage.

**Alternatives**:
1. Build mem0 from source: `git clone https://github.com/mem0ai/mem0 && docker build`
2. Use OpenMemory MCP: `npx @openmemory/install`
3. Wait for official amd64 image

**Lesson**: Always verify Docker image platform support before adding to production stack.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v1.3 | 2026-01-25 | Added F-008: MXFP4 DeepSeek-V3.2-Exp architecture mismatch |
| v1.2 | 2026-01-24 | Added F-007: httpx.AsyncClient incompatibility with llama.cpp |
| v1.1 | 2026-01-24 | Added F-006: Mem0 Docker platform incompatibility |
| v1.0 | 2026-01-23 | Initial lessons-learned registry |

---

## F-007: httpx.AsyncClient Incompatibility with llama.cpp (v16.2.6)

**Date**: 2026-01-24  
**Severity**: BLOCKING  
**Component**: Agent Orchestrator inference node

**Symptoms**:
```
HTTP 400 Bad Request from llama.cpp server when using httpx.AsyncClient
```

**Root Cause**: `httpx.AsyncClient` has HTTP/2 connection negotiation issues with llama.cpp server. The server returns 400 errors intermittently during async HTTP/2 upgrades.

**Attempted Fixes**:
| Attempt | Result |
|---------|--------|
| Force HTTP/1.1 | Still fails intermittently |
| Increase timeouts | No effect |
| Use `aiohttp` | Requires major refactor |

**Resolution**: Replaced `httpx.AsyncClient` with synchronous `httpx.Client` wrapped in `asyncio.to_thread()`.

**The Fix**:
```python
# WRONG (causes 400 errors)
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)

# CORRECT (v16.2.6)
response = await asyncio.to_thread(
    _handle_streaming_sync, url, data, timeout
)
```

**Files Changed**:
- `src/agent/nodes/inference.py`: Lines 211-281 (new sync handlers)

**Lesson**: For local llama.cpp inference servers, prefer synchronous HTTP clients. The thread pool overhead is negligible compared to LLM inference time.

---

## F-008: MXFP4 DeepSeek-V3.2-Exp Architecture Mismatch

**Date**: 2026-01-25  
**Version**: v16.3.3  
**Severity**: BLOCKING  
**Component**: Operation Speed Demon (MXFP4 Benchmark)

**Symptoms**:
```
llama_model_load: error loading model: error loading model architecture: unknown model architecture: 'deepseek3_2'
```

**Context**:
- Downloaded model: `stevescot1979/DeepSeek-V3.2-MXFP4-GGUF` (342GB, 18 chunks → reassembled)
- Model architecture in GGUF: `deepseek3_2`
- llama.cpp build (557515be1): Only supports `deepseek2`

**Root Cause**:
The MXFP4 quantization was created from **DeepSeek-V3.2-Exp** (experimental branch), which uses a new `deepseek3_2` architecture requiring sparse attention primitives not yet in mainline llama.cpp.

**Related Issue**: [ggml-org/llama.cpp#16331](https://github.com/ggml-org/llama.cpp/issues/16331) - "Feature Request: DeepSeek V3.2-Exp support"

**What Failed**:
| Step | Result |
|------|--------|
| Downloaded 342GB model via hf_transfer (57 MB/s) | ✓ Success |
| Reassembled 18 chunks into single GGUF | ✓ Success |
| Model load in llama.cpp | ✗ Architecture unknown |

**Lesson**: Do NOT download "Experimental" architecture quantizations until upstream llama.cpp support is confirmed. Check the GGUF metadata `general.architecture` field before downloading large models.

**Verification Before Download**:
```bash
# Check model architecture BEFORE downloading
curl -sL "https://huggingface.co/<repo>/resolve/main/README.md" | grep -i architecture
# Look for: deepseek2 (supported) vs deepseek3_2 (NOT supported)
```

**Cleanup Applied**:
- Deleted 684GB (342GB model + 342GB chunks)
- Removed sidecar service from `docker/omni-stack.yaml`
- Marked P2 (MXFP4 benchmark) as BLOCKED/DEFERRED in roadmap

---

## S-006: Manual Model Override via GraphState (v16.2.6)

**Date**: 2026-01-24  
**Impact**: MEDIUM

**What Worked**: Adding `model: str` field to LangGraph `GraphState` TypedDict and implementing early-exit logic in classification node.

**Key Configuration**:
```python
# state.py
class GraphState(TypedDict, total=False):
    model: str  # "auto", "deepseek", "qwen"

# classification.py
MODEL_ALIASES = {
    "deepseek-v3.2": "deepseek",
    "deepseek": "deepseek",
    "qwen2.5-coder-7b": "qwen",
    "qwen": "qwen",
}

if requested_model and requested_model.lower() != "auto":
    endpoint_key = MODEL_ALIASES.get(requested_model.lower())
    if endpoint_key:
        return early_exit_with_override(endpoint_key)
```

**Why It Worked**: LangGraph silently drops fields not declared in the TypedDict schema. Explicit declaration ensures the field propagates through the graph.

**Lesson**: Always declare ALL expected state fields in LangGraph TypedDict, even optional ones. LangGraph is strict about schema adherence.

---

### F-010: Memgraph AVX512 General Protection Fault on Zen 5

**Date**: 2026-01-24  
**Version**: v16.3.2  
**Severity**: BLOCKING  
**Impact**: Memgraph container crash loop (Exit 139 - SIGSEGV)

**Symptoms**:
```bash
docker ps
# memgraph  Restarting (139) Less than a second ago

sudo dmesg | grep memgraph
# traps: memgraph[186102] general protection fault ip:78715935a9a2 sp:7ffcd5f47010 error:0 in libc.so.6
```

**Environment**:
- CPU: AMD Threadripper PRO 9995WX (Zen 5, 96 cores)
- Container: `memgraph/memgraph:3.7.2` (Ubuntu 22.04 base, glibc 2.39)
- Host: Ubuntu 24.04, glibc 2.39

**Root Cause Analysis**:
1. Memgraph binary compiled with AVX512 instructions
2. Zen 5 has AVX512 support but with different microarchitecture than expected
3. glibc's optimized string routines use AVX512 by default
4. Specific instruction sequence causes General Protection Fault

**Attempted Fixes**:

| Attempt | Result |
|---------|--------|
| Pin to version 3.7.2 | Still crashed |
| Use `-malloc` variant (jemalloc) | Still crashed |
| Wipe volumes | Still crashed |
| Change permissions to 777 | Partial fix (log write worked) |
| `GLIBC_TUNABLES=glibc.cpu.hwcaps=-AVX512F,-AVX512VL` | Partial |
| `GLIBC_TUNABLES=glibc.cpu.hwcaps=-AVX512F,-AVX512VL,-AVX512BW,-AVX512CD,-AVX512DQ` | **SUCCESS** |

**Solution**:
```yaml
# docker-compose.yaml
memgraph:
  image: memgraph/memgraph:3.7.2
  environment:
    GLIBC_TUNABLES: "glibc.cpu.hwcaps=-AVX512F,-AVX512VL,-AVX512BW,-AVX512CD,-AVX512DQ"
  volumes:
    - /nvme/memgraph/data:/var/lib/memgraph
    - /nvme/memgraph/log:/var/log/memgraph
    # NOTE: Do NOT mount /etc/memgraph - causes config conflicts
```

Also ensure volume permissions:
```bash
sudo chmod -R 777 /nvme/memgraph/
```

**Lesson**: Zen 5 (Threadripper PRO 9995WX) may have AVX512 compatibility issues with binaries compiled for older microarchitectures. Use `GLIBC_TUNABLES` to disable problematic AVX512 extensions. This forces glibc to use scalar or AVX2 fallback implementations.
