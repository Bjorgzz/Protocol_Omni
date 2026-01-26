# Protocol OMNI: Lessons Learned Registry

> **Purpose**: Chronicle of failures, pivots, and hard-won knowledge for AI agent training  
> **Last Updated**: 2026-01-26  
> **Versions Covered**: v13.0 → v16.3.5

This document captures architectural decisions, failed experiments, and pivots to prevent agents from repeating mistakes.

---

## Quick Reference: What NOT To Do

| Anti-Pattern | Why It Failed | Correct Approach |
|--------------|---------------|------------------|
| KTransformers on Blackwell | ~~sm_120 kernels missing~~ **LAZARUS SUCCESS** | kt-kernel 0.5.1 + PyTorch 2.11 nightly (cu128) ✅ |
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
| Phased Dockerfile with comments | KTransformers never installed | Use phase-tagged images (`:phase1`, `:phase2`) |
| CUDA 12.1 for Blackwell (F-012) | sm_120 not supported | Use CUDA 12.8+ base image |
| Shallow git clone with submodules (F-013) | Breaks pybind11, llama.cpp deps | Use `git clone --recursive` (no depth limit) |
| Build-time GPU validation (F-014) | No CUDA device during Docker build | Validate in CMD/ENTRYPOINT at runtime |
| Missing hwloc/pkg-config (F-015) | CMake can't find HWLOC | Add `pkg-config libhwloc-dev` to apt-get |
| kt-kernel only (F-016) | Main package in archive/ needs cmake | Install BOTH kt-kernel AND archive/ with cmake |
| Archive third_party path (F-017) | CMake expects ../../third_party | **RESOLVED**: `rm -rf` + `cp -r` third_party into archive/ ✅ |
| balance_serve/sched_ext (F-018) | C++20 extension required for ktransformers server | Build separately or wait for prebuilt wheel |

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

### F-018: balance_serve/sched_ext C++ Extension Required for KTransformers Server

**Date**: 2026-01-26  
**Version**: v16.3.6  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Phase 3 - KTransformers full inference stack

**Symptoms**:
```
ModuleNotFoundError: No module named 'sched_ext'
```

**Import Chain**:
```
ktransformers.local_chat
  → ktransformers.models.custom_cache
    → ktransformers.server.balance_serve.settings
      → import sched_ext  # FAILS
```

**Root Cause**: The `sched_ext` module is a C++ extension built from `csrc/balance_serve/`. It requires:
- C++20 compiler (g++-11/12/13)
- PyTorch ABI matching (critical)
- Separate CMake build process

**What Works**:
- kt-kernel 0.5.1 (standalone CUDA kernels) ✅
- SGLang server (for HF models) ✅
- kt CLI (version, doctor) ✅

**What Doesn't Work**:
- ktransformers.local_chat ❌
- ktransformers.server.api ❌
- Full inference benchmark ❌

**Containers Built**:
| Tag | Size | Contents |
|-----|------|----------|
| `phase2` | 37.1GB | kt-kernel 0.5.1 + PyTorch 2.11 nightly |
| `phase3` | 48.3GB | kt-kernel 0.5.1 + SGLang + sqlalchemy |

**Workarounds**:
1. **Use llama.cpp**: Proven working for DeepSeek-R1 (10.9 tok/s baseline)
2. **Build balance_serve**: Separate CMake build from `csrc/balance_serve/` (complex, C++20)
3. **Wait for prebuilt**: Monitor KTransformers releases for `sched_ext` wheel

**Lesson**: KTransformers in 2026 is a modular monorepo. The kt-kernel provides CUDA kernels, but the full inference server requires balance_serve C++ extension which needs separate build. Verify the FULL import chain before assuming inference capability.

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

### S-007: Verdent SSH Allowlist via permission.json

**Date**: 2026-01-26  
**Impact**: HIGH

**Problem**: Verdent's bash tool sandboxes SSH/network commands by default ("Blocked CRITICAL risk"). Even simple allowlists can fail on complex shell patterns (`nohup`, `&`, redirections).

**What Worked**: Using the `permissions.allow` format with `Bash()` wrapper to fully bypass injection detection.

**Setup**:
```bash
# Requires SSH key in macOS Keychain
ssh-add --apple-use-keychain ~/.ssh/id_ed25519

# Create permission allowlist (CORRECT FORMAT)
cat > ~/.verdent/permission.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(ssh omni@192.168.3.10 *)",
      "Bash(ssh -o BatchMode=yes omni@192.168.3.10 *)",
      "Bash(scp * omni@192.168.3.10:*)"
    ],
    "deny": []
  }
}
EOF
```

**Usage (native bash, full shell syntax supported)**:
```bash
ssh -o BatchMode=yes omni@192.168.3.10 "hostname"
ssh -o BatchMode=yes omni@192.168.3.10 "docker ps --format 'table {{.Names}}'"
ssh -o BatchMode=yes omni@192.168.3.10 "nohup docker build ... > /tmp/log 2>&1 &"
```

**Why It Worked**: The `Bash()` wrapper in `permissions.allow` tells Verdent to treat matched commands as fully trusted, bypassing both the sandbox AND injection detection.

**Common Mistake**: Using `allow_rules` format (legacy/undocumented) — this only bypasses the sandbox, not injection detection. Complex patterns with `nohup`, `&`, `>` still get blocked.

**Lesson**: Always use the documented `permissions.allow` format with `Bash()` wrapper for full command trust.

---

### S-008: Operation Lazarus - KTransformers SM_120 Build SUCCESS

**Date**: 2026-01-26  
**Impact**: CRITICAL

**Problem Solved**: KTransformers was previously blocked on Blackwell (sm_120) due to missing CUDA kernels. Operation Lazarus successfully built kt-kernel 0.5.1 with native sm_120 support.

**What Worked**:
1. **CUDA 12.8 base image**: `nvidia/cuda:12.8.0-devel-ubuntu22.04` (CUDA 12.1 lacks sm_120)
2. **PyTorch nightly cu128**: `pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128`
3. **Full recursive clone**: `git clone --recursive` (shallow clone breaks submodules)
4. **F-017 fix**: Copy third_party into archive/ for CMake path resolution

**Container**: `omni/ktransformers-lazarus:phase2` (37.1GB)

**Verification**:
```python
import kt_kernel
print(kt_kernel.__version__)  # 0.5.1

import torch
print(torch.cuda.get_arch_list())  # ['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120']
```

**Doctor Output**:
```
GPU detection: NVIDIA RTX PRO 6000 Blackwell + RTX 5090
kt-kernel: v0.5.1 (AVX512_BF16)
NUMA Topology: 1 node(s) [NPS1]
```

**Remaining Work**: Full inference server needs `sqlalchemy` and `sched_ext` deps (Phase 3).

**Lesson**: For bleeding-edge GPU architectures, use CUDA nightly + PyTorch nightly builds. Avoid pre-built Docker images with older CUDA versions.

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
| v1.10 | 2026-01-26 | Added F-018: balance_serve/sched_ext blocker. Lazarus Phase 3 PARTIAL. |
| v1.9 | 2026-01-26 | **F-017 RESOLVED**: Archive third_party path fixed with rm+cp. Lazarus Phase 2 BUILD SUCCESS! |
| v1.9 | 2026-01-26 | Added S-008: KTransformers kt-kernel 0.5.1 with SM_120 (Blackwell) support confirmed |
| v1.8 | 2026-01-26 | Added S-007: Verdent SSH bypass via osascript wrapper |
| v1.8 | 2026-01-26 | Added F-015: Missing pkg-config and libhwloc-dev for kt-kernel build |
| v1.7 | 2026-01-26 | Added F-014: Build-time GPU validation fails in Docker (no CUDA device) |
| v1.6 | 2026-01-26 | Added F-013: Shallow Git clone breaks submodules (kt-kernel build failure) |
| v1.5 | 2026-01-26 | Added F-012: CUDA 12.1 does not support SM_120 (Blackwell) |
| v1.4 | 2026-01-25 | Added F-009: KTransformers model compatibility matrix (R1-0528 blocked, V3.2 sm120 blockers) |
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

---

## F-009: KTransformers Model Compatibility Matrix (Operation Lazarus)

**Date**: 2026-01-25  
**Version**: v16.3.5  
**Severity**: INFORMATIONAL  
**Component**: Operation Lazarus target model selection

**Context**: Sentinel Audit to determine optimal DeepSeek model for KTransformers injection on Blackwell (sm_120).

**Model Compatibility Matrix**:

| Model | Architecture | KTransformers | SM120 | Status |
|-------|-------------|---------------|-------|--------|
| DeepSeek-R1 | `deepseek2` | FULL | COMPATIBLE | **RECOMMENDED** |
| DeepSeek-V3-0324 | `deepseek2` | FULL | COMPATIBLE | Stable Fallback |
| DeepSeek-V3.2 | `deepseek2` + DSA | PARTIAL | BLOCKED | High Risk |
| DeepSeek-R1-0528 | `deepseek2` | BLOCKED | N/A | UD 2.0 incompatible |

**DeepSeek-V3.2 Blockers (SM120)**:
- FlashMLA: Does not support sm_120 (Issue #1680)
- DeepGEMM: Does not support sm_120 (Issue #236)
- FP8 KV-cache: Broken on sm_120, must use BF16
- FlashInfer: Alternative but crashes with "out of shared memory"

**DeepSeek-R1-0528 Blocker**:
- Issue #1360: "invalid weight type"
- Root cause: UD 2.0 quantization format incompatible with KTransformers (Issue #1195)

**Recommended Target**:
```
Repository: unsloth/DeepSeek-R1-GGUF
Quantization: Q4_K_M (377GB) or Q3_K_M (298GB)
Architecture: deepseek2
```

**Download Command**:
```bash
huggingface-cli download unsloth/DeepSeek-R1-GGUF \
  --include "DeepSeek-R1-Q4_K_M/*" \
  --local-dir /nvme/models/deepseek-r1-q4km
```

**Lesson**: When selecting models for KTransformers on bleeding-edge hardware (sm_120), prefer models with proven `deepseek2` architecture and avoid experimental architectures (V3.2's sparse attention) or new quantization formats (UD 2.0). DeepSeek-R1 provides maximum reasoning capability with full compatibility.

---

## F-011: Docker Path Mismatch - KTransformers Not Installed

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus container (`omni/ktransformers-lazarus:nightly`)

**Symptoms**:
```
ModuleNotFoundError: No module named 'ktransformers'
```

**Root Cause**: The Phase 1 Lazarus Dockerfile (L59-61) had KTransformers installation **commented out** as a placeholder:
```dockerfile
# Placeholder: KTransformers will be cloned/installed at runtime or in Phase 2
# RUN git clone https://github.com/kvcache-ai/ktransformers.git && \
#     cd ktransformers && pip install -e .
```

The image was built for Phase 1 verification (PyTorch sm_120 support) but never updated for Phase 2 (actual KTransformers installation).

**Forensics Command**:
```bash
docker run --rm --entrypoint /bin/bash omni/ktransformers-lazarus:nightly -c \
  'find / -name "ktransformers" -type d 2>/dev/null && pip list | grep -i ktrans'
```

**Forensics Result**:
| Check | Result |
|-------|--------|
| `find ktransformers` | Empty (not found) |
| `pip list` | Not installed |
| PyTorch | Installed (nightly cu128) |

**Resolution**: Updated `Dockerfile.ktransformers-lazarus` in two stages:

**Stage 1** (repo structure change): KTransformers is now a monorepo with `kt-kernel/` subdirectory:
```dockerfile
cd ktransformers/kt-kernel && pip install .
```

**Stage 2** (CUDA architecture): kt-kernel uses `CPUINFER_CUDA_ARCHS` env var (not `CMAKE_CUDA_ARCHITECTURES`):
```dockerfile
ENV CPUINFER_CUDA_ARCHS="120"
ENV CPUINFER_USE_CUDA="1"
RUN git clone --depth 1 https://github.com/kvcache-ai/ktransformers.git && \
    cd ktransformers/kt-kernel && pip install --no-cache-dir -v .
```

**Key Discovery**: kt-kernel's `setup.py` line 639 reads:
```python
archs_env = os.environ.get("CPUINFER_CUDA_ARCHS", "80;86;89;90")
```
Default is `80;86;89;90`, must override to `120` for Blackwell.

**Rebuild Command**:
```bash
docker build -f Dockerfile.ktransformers-lazarus -t omni/ktransformers-lazarus:phase2 docker/
```

**Lesson**: When using phased container builds, track phase status in image tags (`:phase1`, `:phase2`) rather than generic tags (`:nightly`). Also verify that CUDA architecture environment variables match the target GPU (sm_120 for Blackwell = `CPUINFER_CUDA_ARCHS=120`).

---

## F-012: CUDA 12.1 Does Not Support SM_120 (Blackwell)

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Build v3

**Symptoms**:
```
nvcc fatal: Unsupported gpu architecture 'compute_120'
CMake Error at CMakeTestCUDACompiler.cmake:59 (message):
    make[1]: *** [CMakeFiles/cmTC_908fe.dir/build.make:82: CMakeFiles/cmTC_908fe.dir/main.cu.o] Error 1
```

**Root Cause**: Base image `pytorch/pytorch:2.1.1-cuda12.1-cudnn8-devel` uses CUDA 12.1 toolkit. CUDA 12.1 does not include `compute_120` (Blackwell sm_120) in its architecture list.

**SM_120 Support Matrix**:
| CUDA Version | SM_120 Support | Notes |
|--------------|----------------|-------|
| 12.1 | ❌ NO | Only up to sm_90 (Hopper) |
| 12.4 | ❌ NO | Only up to sm_90 |
| 12.6 | ⚠️ Partial | Early sm_120 preview |
| 12.8 | ✅ YES | Full sm_120 support |

**Resolution**: Changed base image from `pytorch/pytorch:2.1.1-cuda12.1-cudnn8-devel` to `nvidia/cuda:12.8.0-devel-ubuntu22.04` and manually installed PyTorch nightly with cu128 index.

**Correct Dockerfile Pattern**:
```dockerfile
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04
RUN pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128
```

**Lesson**: Blackwell (RTX PRO 6000, sm_120) requires CUDA 12.8+. Do not use PyTorch pre-built images with older CUDA versions for bleeding-edge GPU architectures. Build from NVIDIA base images and install PyTorch nightly separately.

---

## F-013: Shallow Git Clone Breaks Submodules (kt-kernel Build Failure)

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Build v3/v4 - KTransformers kt-kernel

**Symptoms**:
```
CMake Error: Could not find pybind11
fatal: reference is not a tree: <sha>
```
Or pip install crashes without clear error, Docker exports "zombie" image.

**Root Cause**: Using `git clone --depth 1 --shallow-submodules` creates truncated Git history. KTransformers submodules (pybind11, llama.cpp, custom_flashinfer) reference specific commit SHAs that don't exist in shallow clones.

**The Wrong Pattern**:
```dockerfile
RUN git clone --depth 1 --recurse-submodules --shallow-submodules \
    https://github.com/kvcache-ai/ktransformers.git && \
    git submodule update --init --recursive  # CANNOT FIX SHALLOW SUBMODULES
```

**The Correct Pattern**:
```dockerfile
RUN git clone --recursive https://github.com/kvcache-ai/ktransformers.git && \
    cd ktransformers/kt-kernel && \
    pip install -v .
```

**Why `git submodule update` Doesn't Fix It**:
When submodules are initialized with `--shallow-submodules`, they lack history. Running `git submodule update --init --recursive` afterwards cannot fetch the missing commits because the parent repository's reference points to SHAs that don't exist in the truncated submodule history.

**Trade-off**:
- **Shallow clone**: ~50MB download, broken submodules
- **Full clone**: ~500MB download, working submodules

**Lesson**: For projects with submodules that reference specific commits (not HEAD), always use `git clone --recursive` without depth limits. The extra download time is negligible compared to debugging broken builds.

---

## F-014: Build-Time GPU Validation Fails in Docker (No CUDA Device)

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Build v4 - Docker build step

**Symptoms**:
```
CUDA Arch List: []
AssertionError: sm_120 not found!
```

**Root Cause**: Docker builds do not have GPU access by default. The `RUN` instruction executes in a non-GPU context, so `torch.cuda.get_arch_list()` returns an empty list `[]`.

**The Wrong Pattern**:
```dockerfile
# Build-time validation (FAILS - no GPU during build)
RUN python -c "import torch; archs = torch.cuda.get_arch_list(); assert 'sm_120' in archs"
```

**Why It Fails**:
1. Docker build runs on CPU-only (unless using `docker buildx` with `--device` flags)
2. `torch.cuda.get_arch_list()` queries the CUDA device at runtime
3. No device = empty list, regardless of compiled-in architecture support

**The Correct Pattern**:
```dockerfile
# Runtime validation (runs WITH GPU via --gpus all)
CMD ["python", "-c", "import torch; print('CUDA archs:', torch.cuda.get_arch_list()); import kt_kernel; print('LAZARUS READY')"]
```

**Important Distinction**:
- **Compiled-in support** (baked into wheel): PyTorch cu128 nightly wheels are compiled with sm_120 support. This is fixed at wheel-build time by NVIDIA/PyTorch maintainers.
- **Runtime detection** (`get_arch_list()`): Queries the actual GPU device present. Returns `[]` if no GPU available.

**The sm_120 support IS present** in the PyTorch cu128 wheel - it just can't be verified during build because there's no GPU to query.

**Resolution**: Move all GPU validation to `CMD`/`ENTRYPOINT` which runs when the container starts with `--gpus all`.

**Lesson**: Never validate GPU capabilities during Docker build. All CUDA-dependent checks must happen at container runtime when GPU is attached via `--gpus all` or NVIDIA Container Toolkit.

---

## F-015: Missing pkg-config and libhwloc-dev for kt-kernel Build

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Build v5 - kt-kernel CMake

**Symptoms**:
```
CMake Error at CMakeLists.txt:573 (message):
    FindHWLOC needs pkg-config program and PKG_CONFIG_PATH must contain the
    path to hwloc.pc file.
```

**Root Cause**: kt-kernel's CMakeLists.txt requires HWLOC (Hardware Locality) library for CPU topology detection. The minimal Ubuntu base image lacks `pkg-config` and `libhwloc-dev`.

**Missing Dependencies**:
| Package | Purpose |
|---------|---------|
| `pkg-config` | CMake dependency resolution |
| `libhwloc-dev` | Hardware topology library (headers + .pc file) |

**Resolution**: Added to Dockerfile apt-get install:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake build-essential ninja-build libnuma-dev python3 python3-pip python3-dev \
    pkg-config libhwloc-dev && \
    rm -rf /var/lib/apt/lists/*
```

**Lesson**: When building complex C++/CUDA projects like kt-kernel, review CMakeLists.txt for `find_package()` calls. Common missing dependencies for ML kernels include: `pkg-config`, `libhwloc-dev`, `libnuma-dev`, `libopenblas-dev`.

---

## F-016: KTransformers Repo Restructured - Archive Package Requires cmake

**Date**: 2026-01-26  
**Version**: v16.3.5  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Phase 2 - ktransformers main package install

**Symptoms**:
```
error: [Errno 2] No such file or directory: 'cmake'
CMake args: ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=...']
ERROR: Failed building editable for ktransformers
```

**Root Cause**: The KTransformers repository was restructured:
- **kt-kernel/** - Standalone CUDA inference kernels (what `omni/ktransformers-lazarus:final` has)
- **archive/** - Original main package with model loading, server, CLI, and C++ extensions

The archive package has C++ extensions in `csrc/ktransformers_ext/` that require cmake to build. The Dockerfile was missing cmake in apt-get install.

**KTransformers Package Structure (2026)**:
| Directory | Contents | Install Method |
|-----------|----------|----------------|
| `kt-kernel/` | CUDA kernels (sm_120 support) | `pip install .` |
| `archive/` | Model loading, server, CLI | `pip install -e .` |
| `kt-sft/` | Fine-tuning (not needed for inference) | Skip |

**Resolution**: Add `cmake` to Dockerfile apt-get install:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    git wget curl build-essential ninja-build \
    cmake \
    pkg-config libhwloc-dev \
    && rm -rf /var/lib/apt/lists/*
```

**Lesson**: The KTransformers repo has been restructured into a monorepo. The `kt-kernel` package provides CUDA kernels but NOT model loading. The main package (with model loading) is in `archive/` and has its own C++ extensions requiring cmake. Always check both packages when building a complete inference container.
