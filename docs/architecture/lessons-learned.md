# Protocol OMNI: Lessons Learned Registry

> **Purpose**: Chronicle of failures, pivots, and hard-won knowledge for AI agent training  
> **Last Updated**: 2026-01-27  
> **Versions Covered**: v13.0 → v16.4.12

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
| Mem0 Docker deployment | No linux/amd64 image (F-006 STILL BLOCKED) | Use OpenMemory (CaviraOSS) — local-first, SQLite |
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
| balance_serve/sched_ext (F-018/F-023) | Deep dependency chain (prometheus-cpp, PhotonLibOS, xxHash, TBB) | **llama.cpp only** - KTransformers 0.4.1 GGUF path blocked |
| kt-kernel FP8→INT8 conversion (F-019) | Segfault at MoE layer 3 | Use llama.cpp GGUF (pre-quantized HF weights also 642GB) |
| FP8 weights on 377GB RAM (F-020) | 642GB > RAM, SGLang OOM | **Superseded by F-022** - INT8 also 642GB, use llama.cpp GGUF |
| Meituan INT8 on 377GB RAM (F-022) | 642GB > 584GB addressable, system crash | **llama.cpp GGUF only** - SGLang loading requires full model in RAM |
| ik_llama.cpp split mode graph (F-024) | Not supported for MoE, OOM on layer mode | Standard llama.cpp for DeepSeek-R1 MoE |
| NVIDIA Dynamo (F-025) | Datacenter-scale only, needs homogeneous clusters | llama.cpp for single-node asymmetric GPUs |
| ExLlamaV3 (F-026) | DeepSeek architecture not supported | llama.cpp or wait for arch support |
| KTransformers v0.5.1 (F-027) | ABI mismatch + sched_ext chain (4-8h fix, ~10-30% gain) | **DEFERRED** - Low ROI vs stable 10 tok/s |
| 20 tok/s Blackwell (S-014) | Requires 2x PRO 6000 symmetric | Our asymmetric 96+32GB → 10 tok/s is expected |

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

### F-019: kt-kernel FP8→INT8 Conversion Segfault (MoE Experts)

**Date**: 2026-01-26  
**Version**: v16.4.1  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Phase 4.5 - Weight quantization

**Symptoms**:
```
Processing layer 3 (1/59)...
Converting layer 3 with 256 experts via online quantization...
bash: line 1:  1773 Segmentation fault (core dumped)
```

**Root Cause**: The `convert_cpu_weights.py` script in kt-kernel crashes when processing FP8 input weights during MoE expert conversion. The segfault occurs consistently at the same layer regardless of thread count.

**What Was Attempted**:
| Input Type | Result |
|------------|--------|
| `--input-type fp8` | Segfault at layer 3 |
| `--input-type bf16` | Works but thrashes 200GB swap (ETA: 49 hours for 59 layers) |

**Environment**:
- Model: DeepSeek-R1 HF weights (642GB FP8, 163 shards)
- Container: `ktransformers-sglang`
- Script: `/workspace/ktransformers/kt-kernel/scripts/convert_cpu_weights.py`

**Resolution**: Abandoned kt-kernel conversion path. Pivoted to downloading pre-quantized `meituan/DeepSeek-R1-Block-INT8` weights.

**Lesson**: kt-kernel's FP8→INT8 conversion is unstable for 671B MoE models. For large-scale deployments, use pre-quantized weights from providers (Meituan, Unsloth) rather than attempting runtime conversion.

---

### F-020: FP8 RAM Constraint - Model Size Exceeds System Memory

**Date**: 2026-01-26  
**Version**: v16.4.2  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Phase 4.5 - SGLang loading

**Symptoms**:
```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 7.03 GiB. 
GPU 0 has a total capacity of 94.97 GiB of which 5.74 GiB is free. 
Including non-PyTorch memory, this process has 88.54 GiB memory in use.
```

**Root Cause**: DeepSeek-R1 FP8 weights total 642GB. System has 377GB RAM + 207GB NVMe swap = 584GB addressable, but:
1. SGLang needs GPU memory for dense layers + KV cache
2. CPU offload (`--cpu-offload-gb 500`) still requires GPU for MoE expert routing
3. Even with aggressive offload, GPU OOMs during expert allocation

**SGLang Attempts**:
| Settings | Result |
|----------|--------|
| `--cpu-offload-gb 300` | OOM at 88.5GB GPU |
| `--cpu-offload-gb 500 --mem-fraction-static 0.7` | OOM (same) |
| `--enable-mixed-chunk` added | OOM (same) |

**Why llama.cpp Works**: llama.cpp uses GGUF with aggressive quantization (Q4_K_M = 377GB). SGLang tries to load FP8 which is 1.7x larger.

**Resolution**: ~~Pivot to `meituan/DeepSeek-R1-Block-INT8` pre-quantized weights (~350GB)~~ **SUPERSEDED**: F-022 proved Meituan INT8 is also 642GB. **llama.cpp GGUF is the only viable path.**

**Lesson**: For SGLang + DeepSeek 671B on consumer hardware (377GB RAM), neither FP8 nor INT8 HF weights fit. Use llama.cpp GGUF (Q4_K_M = 377GB) which streams layers instead of loading all at once.

---

### F-022: Meituan INT8 Still Exceeds RAM - System Crash

**Date**: 2026-01-27  
**Version**: v16.4.9  
**Severity**: CRITICAL  
**Component**: Operation Lazarus Phase 5 - SGLang INT8 loading

**Symptoms**:
```
[2026-01-26 23:15:21] Rank 0 scheduler is dead.
[2026-01-26 23:16:07] Exit code: -9
```
System became completely unresponsive - SSH timeout, all services unreachable.

**Root Cause**: `meituan/DeepSeek-R1-Block-INT8` is NOT ~350GB as assumed - it's **642GB** (same as FP8). SGLang loads ALL weights into memory before distributing to CPU offload.

**Memory Timeline**:
| Time | RAM Used | Swap Used | GPU VRAM |
|------|----------|-----------|----------|
| Start | 23GB | 2.6GB | 14GB |
| +60s | 319GB | 2.6GB | 14.7GB |
| +90s | 375GB | 8GB | 14.8GB |
| Crash | 376GB+ | 8.9GB+ | 14.9GB |

Even with 207GB NVMe swap enabled (377GB + 207GB = 584GB), the 642GB model exceeded addressable memory.

**Critical Discovery**: The assumption that "Meituan INT8 weights ~350GB" was **FALSE**. The model remains 642GB regardless of INT8 vs FP8 because:
1. INT8 refers to activation quantization, NOT weight quantization
2. Model weights are stored at full precision with INT8 scale factors
3. Total checkpoint size: 163 files × ~4GB each = 642GB

**System Impact**: Severe memory pressure caused:
- OOM killer (SIGKILL -9) on scheduler process
- System swap thrashing
- Complete unresponsiveness requiring physical reboot

**Resolution**: **SGLang + DeepSeek-R1 671B is BLOCKED** on this hardware. Options:
1. **llama.cpp (RECOMMENDED)**: GGUF streaming loader doesn't require full model in RAM
2. **NVIDIA Dynamo**: Investigate disaggregated serving for asymmetric hardware
3. **Distilled models**: DeepSeek-R1-Distill-8B/32B fit in available memory
4. **Cluster expansion**: Add RAM to reach 1TB+ for full model loading

**Lesson**: Never assume model size from quantization format name. Always verify actual checkpoint size before loading. SGLang's loading strategy requires peak memory ≥ model size, unlike GGUF which streams layers.

---

### F-023: KTransformers sched_ext Dependency Hell - GGUF Path Blocked

**Date**: 2026-01-27  
**Version**: v16.4.10  
**Severity**: BLOCKING  
**Component**: Operation Lazarus Phase 6 - KTransformers GGUF inference

**Context**: After discovering KTransformers supports GGUF format (not just HuggingFace weights), attempted to use it as faster alternative to llama.cpp for Q4_K_M model.

**What Succeeded**:
- Rebuilt `KTransformersOps.so` with SM120 targeting ✅
- Fixed PyTorch ABI mismatch (original import error) ✅
- PyTorch 2.9.1+cu128 with sm_120 verified ✅

**What Failed**: The `sched_ext` module import - required even for basic GGUF inference.

**Dependency Chain Discovered**:
```
sched_ext (balance_serve C++ extension) requires:
├── prometheus-cpp (built from source ✅)
├── TBB (apt install ✅)
├── OpenSSL (apt install ✅)  
├── libaio (apt install ✅)
├── libcurl (apt install ✅)
├── PhotonLibOS (Alibaba async I/O library, cloned ✅)
└── xxHash (cloned ❌ - expects deprecated cmake_unofficial/ structure)
    └── [Unknown additional deps likely]
```

**Architecture Issue**: KTransformers 0.4.1 hardcodes `sched_ext` import in `custom_cache.py` line 25:
```python
from ktransformers.server.balance_serve.settings import sched_ext
```

This is **unconditional** - even `local_chat` for simple GGUF inference triggers the full server scheduling import chain.

**Why This Matters**:
- The GGUF path was theoretically viable: mmap() loading, ~10 tok/s decode
- But the code architecture couples basic inference to server scheduling
- No easy workaround without patching source (risky)

**Resolution**: **KTransformers GGUF path is BLOCKED** on version 0.4.1. The dependency investment (4+ hours estimated) doesn't justify potential 10% performance gain over llama.cpp.

**Alternatives**:
1. **llama.cpp (RECOMMENDED)**: Working at 10.9 tok/s, stable
2. **Wait for KTransformers 0.5+**: May decouple sched_ext from inference
3. **Fork and patch**: Remove sched_ext dependency (high risk)

**Lesson**: Even when CUDA kernels build successfully (sm_120 targeting works!), the full inference path may have deep C++ extension dependencies. Always trace the complete import chain before declaring success.

---

### F-024: ik_llama.cpp Split Mode Graph Not Supported for MoE

**Date**: 2026-01-27  
**Version**: v16.4.10  
**Severity**: BLOCKING  
**Component**: Performance optimization - ik_llama.cpp evaluation

**Context**: Evaluated ik_llama.cpp's `--split-mode graph` feature which claimed 3x-4x performance gains on multi-GPU systems.

**Symptoms**:
```
=======================================================
Split mode 'graph' is not supported for this model
  => changing split mode to 'layer'
=======================================================
```

**Root Cause**: ik_llama.cpp's split mode graph is designed for **dense transformer models**, not Mixture-of-Experts architectures. DeepSeek-R1 uses MoE with 256 experts and Multi-head Latent Attention (MLA), which the graph optimization cannot handle.

**Fallback Attempt (Layer Mode)**:
| GPU Layers | Result |
|------------|--------|
| 19 (default) | OOM: tried to allocate 100GB on 96GB GPU |
| 15 (reduced) | OOM: tried to allocate 31.5GB compute buffer |

Even with MLA flag (`-mla 2`) enabled, layer mode failed due to ik_llama.cpp's different memory allocation strategy (large contiguous blocks vs llama.cpp's streaming approach).

**Why Standard llama.cpp Works**: 
- Streams layers incrementally
- Allocates smaller buffers
- Same model runs fine with `--n-gpu-layers 19 --tensor-split 75,25`

**Resolution**: **ik_llama.cpp is NOT VIABLE** for DeepSeek-R1 MoE on asymmetric GPUs. Standard llama.cpp remains optimal.

**Lesson**: Multi-GPU optimizations often assume dense architectures. MoE models with expert routing create irregular memory access patterns that break graph-based optimizations. Always test with the actual model architecture, not just VRAM calculations.

---

### F-025: NVIDIA Dynamo Not Viable for Single-Node Asymmetric GPUs

**Date**: 2026-01-27  
**Version**: v16.4.10  
**Severity**: INFORMATIONAL  
**Component**: Performance optimization research

**Context**: Evaluated NVIDIA Dynamo as potential optimization path for 96GB + 32GB asymmetric GPU setup.

**Findings**:
- Dynamo is designed for **datacenter-scale multi-node deployments**
- Assumes homogeneous GPU clusters (same GPU type per node)
- Disaggregated prefill/decode requires multiple identical nodes
- Single-node asymmetric configurations not a target use case

**Key Documentation Quotes**:
> "A Datacenter Scale Distributed Inference Serving Framework"
> "GPU Resource Planner: monitors capacity in multi-node deployments"
> "Smart Router: directs traffic across large GPU fleets in multi-node deployments"

**Resolution**: NVIDIA Dynamo is **NOT VIABLE** for our hardware configuration. llama.cpp remains optimal for single-node asymmetric GPUs.

**Lesson**: Enterprise inference frameworks (Dynamo, TensorRT-LLM cluster mode) target homogeneous multi-node deployments. Consumer asymmetric setups need purpose-built solutions like llama.cpp's pipeline parallelism.

---

### F-026: ExLlamaV3 Does Not Support DeepSeek Architecture

**Date**: 2026-01-27  
**Version**: v16.4.10  
**Severity**: INFORMATIONAL  
**Component**: Performance optimization research

**Context**: Evaluated ExLlamaV3 as potential faster inference engine for DeepSeek-R1 MoE.

**Findings**:
ExLlamaV3 supported MoE architectures (as of Jan 2026):
- Mixtral
- ERNIE 4.5 MoE
- GLM 4 MoE, GLM 4.5V MoE
- Qwen 3 MoE

ExLlamaV3 does **NOT** support:
- DeepSeek
- DeepSeek2 (deepseek2 architecture)
- DeepSeek MoE variants

**Resolution**: ExLlamaV3 is **NOT VIABLE** for DeepSeek-R1. Wait for architecture support or continue with llama.cpp.

**Lesson**: Always verify model architecture support before evaluating inference engines. MoE support doesn't mean all MoE architectures - each has unique attention patterns (MLA, GQA, etc.) requiring explicit implementation.

---

### F-027: KTransformers v0.5.1 DEFERRED - Multiple Blockers, Low ROI

**Date**: 2026-01-27  
**Version**: v16.4.10  
**Severity**: INFORMATIONAL  
**Component**: Performance optimization research

**Context**: Evaluated KTransformers v0.5.1 as potential faster inference engine for DeepSeek-R1 GGUF.

**Test Results**:
| Component | Status | Issue |
|-----------|--------|-------|
| kt_kernel 0.5.1 | ✅ WORKS | CUDA kernels import successfully |
| KTransformersOps.so | ❌ BROKEN | PyTorch ABI mismatch: `undefined symbol: _ZN3c104cuda29c10_cuda...` |
| sched_ext | ❌ BLOCKED | Would fail after ABI fix (per F-023) |

**Error Chain**:
```
ktransformers.server.main 
  → ktransformers.util.custom_loader 
    → import KTransformersOps → ABI ERROR

If ABI fixed, next would be:
ktransformers.models.custom_cache 
  → import sched_ext → BLOCKED (F-023)
```

**Fix Effort**: 4-8 hours
- Rebuild KTransformersOps.so with correct PyTorch ABI
- Build balance_serve C++ extension (prometheus-cpp, PhotonLibOS, xxHash, TBB)
- High uncertainty of success

**Expected Gain**: ~10-30% (14-16 tok/s vs 10.35 tok/s baseline)

**Resolution**: **DEFERRED** - Risk/reward ratio unfavorable. llama.cpp at 10.35 tok/s is stable and production-ready. The 20 tok/s benchmark requires symmetric 2x PRO 6000 hardware.

**Lesson**: Multi-layer dependencies (CUDA kernels → C++ extensions → Python modules → server framework) create compounding failure modes. When baseline is stable and gain is marginal, defer complex optimization attempts.

---

## Pivot Registry

### P-001: KTransformers → llama.cpp (Concrete Bunker Doctrine)

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

### S-009: NVMe Swap for Large Model Operations

**Date**: 2026-01-26  
**Impact**: HIGH

**What Worked**: Creating 200GB swap file on NVMe for kt-kernel weight conversion operations that exceed 377GB system RAM.

**Key Configuration**:
```bash
sudo fallocate -l 200G /nvme/swap200g
sudo chmod 600 /nvme/swap200g
sudo mkswap /nvme/swap200g
sudo swapon /nvme/swap200g
```

**Verification**:
```bash
free -h  # Shows 200GB swap
swapon --show  # Lists /nvme/swap200g
```

**Why It Helped**: kt-kernel FP8→BF16 conversion loaded 642GB model into memory. Without swap, OOM killed the process. With swap, it progressed (slowly) at ~2 hours per layer.

**Caveat**: NVMe swap is NOT a substitute for RAM for ML workloads. Use only as emergency overflow. The bf16 conversion with swap thrashing had ETA of 49 hours.

**Lesson**: For emergency large model operations, NVMe swap provides addressable memory but with severe performance penalty. Prefer pre-quantized weights over runtime conversion.

---

### S-010: HuggingFace Download Optimization (50+ MB/s)

**Date**: 2026-01-26  
**Impact**: MEDIUM

**What Worked**: Parallel download workers for large HuggingFace models.

**Key Configuration**:
```bash
# Method 1: Environment variable for parallel workers
HF_HUB_DOWNLOAD_WORKERS=16 huggingface-cli download <repo> --local-dir <path>

# Method 2: hf_transfer for single-file speed (NOT parallel)
HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download <repo>
```

**Performance Results**:
| Method | Speed | Notes |
|--------|-------|-------|
| Default (8 workers) | 38 MB/s | Good baseline |
| 16 workers | 56-60 MB/s | Saturates 500Mbps |
| hf_transfer | 12 MB/s | Single-threaded, faster per-file but slower total |

**Why Parallel > hf_transfer**: For models with many shards (163 files), parallel downloads win. `hf_transfer` is a Rust-based downloader optimized for single large files with better connection handling, but it processes files sequentially. For multi-shard downloads, the parallelism of multiple workers outweighs hf_transfer's per-connection efficiency.

**Lesson**: For multi-shard models (DeepSeek-R1, Llama), use `HF_HUB_DOWNLOAD_WORKERS=16`. Reserve `HF_HUB_ENABLE_HF_TRANSFER=1` for single-file downloads only.

---

### S-011: Container Naming Convention - Lazarus → SGLang

**Date**: 2026-01-26  
**Impact**: LOW (operational clarity)

**What Happened**: During Operation Lazarus, container names evolved:
- `ktransformers-lazarus` - Original Phase 2/3 container name
- `ktransformers-sglang` - Current production container (renamed for clarity)

**Why It Matters**: Agents from previous sessions may reference `ktransformers-lazarus`. That container no longer exists.

**Current Active Containers**:
| Container | Purpose |
|-----------|---------|
| `deepseek-r1` | llama.cpp production (Iron Lung) |
| `ktransformers-sglang` | SGLang experiments, INT8 download |

**Lesson**: When renaming containers mid-operation, document the rename explicitly. Future agents should search for BOTH names when reviewing history.

---

### S-012: System Reboot Recovery - Lazarus Phase 4.5

**Date**: 2026-01-26  
**Impact**: MEDIUM (operational continuity)

**What Happened**: System rebooted during Phase 4.5 (FP8 loading attempts). Post-reboot state:
1. llama.cpp (`deepseek-r1`) auto-started and resumed serving
2. SGLang process died (was running in detached mode, not restart policy)
3. 200GB NVMe swap persisted (configured in fstab)
4. INT8 download had to be restarted manually

**Recovery Actions**:
```bash
# Verify Iron Lung recovered
curl http://localhost:8000/health  # {"status":"ok"}

# Restart INT8 download (SGLang container was up, process was dead)
docker exec -d ktransformers-sglang bash -c 'HF_HUB_DOWNLOAD_WORKERS=16 huggingface-cli download ...'
```

**Lesson**: For long-running downloads, use `screen` or `tmux` inside containers, or configure Docker restart policies. Detached `docker exec -d` processes don't survive container restarts.

---

### S-014: 20 tok/s Blackwell Configuration Discovered

**Date**: 2026-01-27  
**Impact**: INFORMATIONAL (hardware upgrade path)

**Discovery**: YouTube benchmark showing 20 tok/s on DeepSeek-R1-0528 uses:
- **2x RTX PRO 6000 Blackwell** (symmetric 192GB VRAM)
- EPYC multi-socket CPU with NUMA optimization
- Standard llama.cpp (not ik_llama.cpp or Dynamo)
- Q4_K_M quantization

**Our Configuration**:
| Component | 20 tok/s Setup | Our Setup |
|-----------|----------------|-----------|
| GPU Config | 2x PRO 6000 (symmetric) | 1x PRO 6000 + 1x 5090 (asymmetric) |
| Total VRAM | 192GB | 128GB |
| GPU Split | 50/50 (tensor parallel) | 75/25 (pipeline parallel) |
| Performance | 20 tok/s | 10.35 tok/s |

**Why We Can't Match**:
1. Asymmetric GPUs force pipeline parallelism (bucket filling) vs tensor parallelism (matrix splits)
2. 75/25 split creates uneven workload distribution
3. No NVLink between different GPU architectures (5090 ≠ PRO 6000)

**Upgrade Path**: To achieve 20 tok/s, would need second RTX PRO 6000 Blackwell (~$12K) for symmetric 192GB configuration.

**Lesson**: Performance scaling with multi-GPU is highly dependent on symmetry. Asymmetric setups (different VRAM, architectures) incur pipeline parallelism overhead. Our 10 tok/s is the expected ceiling for this hardware combination.

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

### P-005: FP8 HF Weights → Meituan INT8 Pre-Quantized

**Date**: 2026-01-26  
**Version**: v16.4.3

**Original State**: SGLang loading DeepSeek-R1 FP8 HF weights (642GB)  
**New State**: Download `meituan/DeepSeek-R1-Block-INT8` pre-quantized (~350GB)

**Trade-offs**:
| Lost | Gained |
|------|--------|
| Native FP8 precision | Fits in 377GB RAM |
| Manual control of quantization | No conversion step |
| HF reference weights | Pre-optimized for SGLang |

**Blockers That Forced Pivot**:
1. **F-019**: kt-kernel FP8→INT8 conversion segfaults on MoE experts
2. **F-020**: 642GB > 377GB RAM, even with 500GB CPU offload SGLang OOMs

**Reason**: Pre-quantized INT8 weights are the only viable path for SGLang on consumer hardware (377GB RAM, 96GB VRAM). Conversion tools are unstable for 671B MoE models.

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

## F-006: Mem0 Docker Image Platform Incompatibility → STILL BLOCKED

**Date**: 2026-01-24 | **Updated**: 2026-01-27  
**Severity**: **STILL BLOCKED** (Pivot to OpenMemory)  
**Component**: mem0 persistent memory layer

**Symptoms**:
```
Error response from daemon: no matching manifest for linux/amd64 in the manifest list entries
```

**Root Cause**: `mem0/mem0-api-server:latest` only published ARM64 images. No linux/amd64 variant existed.

**2026-01-27 Update (Sentinel Audit ULTRATHINK):**  
GitHub Issue #2884 claims **RESOLVED** on June 25, 2025. However, **VERIFICATION FAILED** — Docker Hub manifest inspection confirms:
- `mem0/mem0-api-server:latest` → **linux/arm64/v8 ONLY**
- Community build `jzacharie/mem0:latest` → Connection timeout

**Pivot Decision:**
| Solution | Status | Verdict |
|----------|--------|---------|
| Mem0 Docker | arm64 only | **REJECTED** |
| Zep Community | Deprecated | **REJECTED** |
| Letta (MemGPT) | amd64, needs Postgres | Viable but heavy |
| **OpenMemory (CaviraOSS)** | amd64, SQLite default | **SELECTED** |

**Deployment Path:**
```bash
# SDK integration (zero dependencies)
pip install openmemory-py

# Or server mode with Docker Compose
git clone https://github.com/CaviraOSS/OpenMemory.git
cd OpenMemory && docker compose up --build -d
```

**Why OpenMemory:**
- Local-first with SQLite (zero ops burden)
- LangChain/LangGraph native SDK integration
- MCP compatible
- Explainable memory traces

**Lesson**: Always verify Docker image platform support independently. Issue tracker "resolved" status doesn't guarantee fix is deployed. Trust but verify.

---

## F-021: Docker Health Check - curl Not Installed in Base Images

**Date**: 2026-01-27  
**Version**: v16.4.4  
**Severity**: OPERATIONAL  
**Component**: Docker Compose health checks

**Symptoms**:
```
OCI runtime exec failed: exec failed: unable to start container process: exec: "curl": executable file not found in $PATH
```

**Affected Containers**:
- `qdrant` - Rust minimal image, no curl
- `mcp-proxy` - Python image, no curl
- `arize-phoenix` - Python image, no curl
- `letta` - Python image, no curl (also had wrong endpoint path - 404)

**Root Cause**: Many Docker base images (especially minimal/distroless) don't include `curl`. Using `curl` in health checks causes false "unhealthy" status even when container is functioning correctly.

**Resolution**: Replace `curl` with alternatives available in each image:

| Image Type | Health Check |
|------------|--------------|
| Python-based | `python -c "import urllib.request; urllib.request.urlopen('http://...')"` |
| Alpine | `wget -q --spider http://...` |
| Rust minimal | Binary self-check: `/app/binary --version` |
| Prometheus | `wget -q --spider http://...` |

**Files Changed**:
- `docker/omni-stack.yaml`: letta, qdrant, mcp-proxy, arize-phoenix health checks

**Lesson**: Never assume `curl` exists in Docker images. Use image-native tools for health checks: `wget` for Alpine, `python urllib` for Python images, binary self-checks for compiled languages.

**Additional Finding (Distroless Images)**:
```
OCI runtime exec failed: exec failed: unable to start container process: exec: "/bin/sh": stat /bin/sh: no such file or directory
```

Distroless images (e.g., `arizephoenix/phoenix`) lack `/bin/sh`. `CMD-SHELL` format requires a shell and will fail. Use `CMD` format instead:

| Format | Requirement | Example |
|--------|-------------|---------|
| `CMD-SHELL` | Needs `/bin/sh` | `["CMD-SHELL", "python -c \"...\""]` |
| `CMD` | Direct binary | `["CMD", "python", "-c", "..."]` |

**Known Limitation (Minimal Rust Images)**:
Containers like `qdrant/qdrant` have no shell, wget, or curl. The only option is binary self-check (`/qdrant/qdrant --version`), which validates the binary exists but NOT that the HTTP/gRPC API is ready. For true API health checks, a custom image with health tooling would be required.

| Image | Available Tools | Best Health Check |
|-------|-----------------|-------------------|
| Python-based | `python` | `["CMD", "python", "-c", "import urllib..."]` |
| Alpine | `wget` | `["CMD", "wget", "-q", "--spider", "..."]` |
| Minimal Rust | Binary only | `["CMD", "/app/binary", "--version"]` (limited) |

---

## S-013: Sentinel Audit 2026-01-27 - Full Stack Review

**Date**: 2026-01-27  
**Version**: v16.4.4  
**Impact**: HIGH

**Audit Scope**: All four Sentinel Audit layers (Software, System, Strategic, Cold Case)

**Key Findings**:

### Driver Upgrade Available
| Component | Installed | Latest | Action |
|-----------|-----------|--------|--------|
| NVIDIA Driver | 580.95.05 | 580.126.09 | **UPGRADE RECOMMENDED** |

Key fixes in 580.126.09:
- YUV 4:2:0 display fix
- Linux kernel 6.19+ compatibility
- Buffer scrubbing performance
- NVLink connection recovery

### NVIDIA Dynamo Evaluation
New inference framework (v0.4.0 → v0.8.1 available):
- **Disaggregated serving** - perfect for 96GB + 32GB asymmetric GPUs
- DeepSeek-R1/V3 supported
- Blackwell sm_120 compatible
- **Recommendation**: Sandbox test v0.7+

### vLLM/SGLang SM120 Status
| Engine | FP8 DeepSeek | Non-FP8 | Status |
|--------|--------------|---------|--------|
| vLLM | BLOCKED (#26211) | Source build | WAIT |
| SGLang | W4A8 issues | Works | **USABLE** |

### Cold Case Resurrections
| Technology | Original Status | New Status |
|------------|-----------------|------------|
| F-006 Mem0 amd64 | BLOCKED | **RESURRECTED** |
| KTransformers+SGLang | BLOCKED | **WAIT** (AMX-exclusive) |

**Lesson**: Quarterly Sentinel Audits catch upstream fixes that silently unblock previously-failed integrations. Always run Cold Case Review on `lessons-learned.md`.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v1.15 | 2026-01-27 | Updated F-021: Added CMD vs CMD-SHELL guidance for distroless images |
| v1.14 | 2026-01-27 | **F-006 RESURRECTED**: Mem0 amd64 Docker image available (Issue #2884 resolved) |
| v1.14 | 2026-01-27 | Added F-021: Docker health check curl not installed |
| v1.14 | 2026-01-27 | Added S-013: Sentinel Audit 2026-01-27 (Driver upgrade, Dynamo eval, vLLM/SGLang status) |
| v1.13 | 2026-01-26 | Added S-009: NVMe swap, S-010: HF download optimization |
| v1.12 | 2026-01-26 | Added P-005: FP8 → Meituan INT8 pivot (RAM constraint) |
| v1.11 | 2026-01-26 | Added F-020: FP8 RAM constraint (642GB > 377GB), F-019: kt-kernel FP8 conversion segfault |
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
