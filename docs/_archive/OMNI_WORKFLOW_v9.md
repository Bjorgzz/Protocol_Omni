# PROJECT OMNI: THE SOVEREIGN NODE (v9.0)

**Objective:** Deploy a self-healing, MCP-native AI Compute Node on Threadripper/Blackwell hardware.

| Field | Value |
|-------|-------|
| **Date** | Jan 16, 2026 |
| **Status** | PHASE 6 COMPLETE (70B Intelligence + Dual GPU) |
| **Cluster Name** | `omni-prime` |
| **Schematic ID** | `d58fba8495bf019d92030f7a24d2bbe8e942331625a6d87fcfd45db9a2b90b6d` |

---

## SYSTEM ARCHITECTURE

| Layer | Component | Specification |
|-------|-----------|---------------|
| L0 (Metal) | Host OS | Proxmox VE 9.x (Kernel 6.8 - Lazarus Pinned) |
| L1 (Guest) | VM OS | Talos Linux v1.12.1 (Kubernetes v1.35.0) |
| L2 (Orch) | Engine | vLLM v0.13.0 (OpenAI-Compatible API) |
| L3 (Brain) | Model | DeepSeek-R1-Distill-Llama-70B (INT4/W4A16, 37GB) |
| L4 (Ops) | Protocol | MCP (Model Context Protocol) |

---

## PHASE 1: THE HOST (METAL HARDENING)

**Goal:** Prepare Proxmox to pass through the Blackwell/5090 pair without crashing.

### 1.1 Kernel & IOMMU Pinning

- **Command:** Check `uname -r`
- **Logic:** IF > 6.8.4, DOWNGRADE to `proxmox-kernel-6.8`
- **Config:** `/etc/default/grub` must include:

```bash
intel_iommu=on    # (or amd_iommu=on)
iommu=pt
pcie_aspm=off     # Prevents power-save crashes
vfio_pci.disable_idle_d3=1  # The Lazarus Fix
```

### 1.2 The Omni-Switch (GPU Unbind Script)

- **File:** `/usr/local/bin/omni-switch`
- **Logic:**
  1. Identify PCI IDs: Blackwell=`0000:f1:00`, 5090=`0000:11:00`
  2. Unbind Audio function (.1) FIRST
  3. Unbind Video function (.0) SECOND
  4. Bind to `vfio-pci`

---

## PHASE 2: THE FACTORY (TALOS IMAGE)

**Goal:** Generate a custom OS image with NVIDIA drivers pre-baked.

### 2.1 The Schematic

- **Endpoint:** `https://factory.talos.dev/schematics`
- **Extensions:**
  - `siderolabs/amd-ucode` (Threadripper Safety)
  - `siderolabs/nvidia-container-toolkit-production` (The GPU Link)
  - `siderolabs/nonfree-kmod-nvidia-production` (The Drivers)
  - `siderolabs/qemu-guest-agent` (Proxmox Visibility)
  - `siderolabs/util-linux-tools` (System Utilities)

---

## PHASE 3: THE TOPOLOGY (VM 105)

**Goal:** Map Virtual NUMA to Physical NUMA (NPS4 Optimization).

### 3.1 The "God Config"

| Parameter | Value |
|-----------|-------|
| CPU | 96 Cores (Host) |
| RAM | 300GB (Hugepages Enabled) |

**PCIe Map:**

| Slot | Device | Notes |
|------|--------|-------|
| `hostpci0` | RTX 6000 Blackwell (96GB) | Primary Compute |
| `hostpci1` | RTX 5090 (32GB) | Secondary Compute, `romfile=palit.rom` |

**Kernel Args:** `nvidia-drm.modeset=0` (The Stability Key)

---

## PHASE 4: THE DEPLOYMENT (KUBERNETES)

**Goal:** Deploy the Brain and the Nervous System.

> **Phase 4.5 COMPLETE:**
> - Kernel args `nvidia-drm.modeset=0` and `console=tty0` applied via `talosctl patch machineconfig -p @provisioning/kernel-args-patch.yaml`
> - GPUs verified: RTX PRO 6000 Blackwell (96GB) + RTX 5090 (32GB)
> - Use `runtimeClassName: nvidia` in pod specs for GPU workloads
> - After reboot: run `kubectl apply -f manifests/driver-validation-creator.yaml` then delete stuck GPU operator pods

> **Phase 5 COMPLETE (DeepSeek Inference):**
> - Runtime: vLLM v0.13.0 (OpenAI-compatible API) - ktransformers image unavailable
> - Model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (32B params, 92GB VRAM with KV cache)
> - Strategy: Single GPU (RTX 6000 Blackwell only) - tensor parallel OOM on 5090
> - Service: `deepseek-v3.ai-workloads.svc.cluster.local:8000`
> - Namespace: `ai-workloads` (privileged PodSecurity for hostPath)
> - Model cached at: `/var/mnt/data/models` (persists across restarts)
> - Config: `--enforce-eager --max-model-len 32768` (CUDA graphs hang on init)

> **Phase 6 COMPLETE (70B Intelligence + Trojan Horse Split):**
> 
> **The Trojan Horse Architecture:**
> | GPU | Role | Model/Service | VRAM Used |
> |-----|------|---------------|-----------|
> | RTX 6000 Blackwell (96GB) | LLM Inference | DeepSeek-R1-Distill-Llama-70B (W4A16) | 37GB + 48GB KV |
> | RTX 5090 (32GB) | Image Generation | Flux/ComfyUI | 32GB |
> 
> **70B LLM Configuration:**
> - Model: `neuralmagic/DeepSeek-R1-Distill-Llama-70B-quantized.w4a16`
> - Quantization: `--quantization compressed-tensors` (W4A16 via Marlin kernels)
> - Context: 32,768 tokens (158K token KV cache capacity)
> - Concurrent 32K requests: 4.85x
> - Endpoint: `http://192.168.3.2:30001/v1`
> - GPU Pinning: `NVIDIA_VISIBLE_DEVICES=GPU-f4f210c1-5a52-7267-979e-fe922961190a`
> 
> **Flux/ComfyUI (Image Gen):**
> - Service: `http://192.168.3.2:30188` (NodePort pending)
> - GPU Pinning: `NVIDIA_VISIBLE_DEVICES=GPU-bfbb9aa1-3d36-b47b-988f-5752cfc54601`
> - Manifest: `k8s/flux-stack.yaml`

### 4.1 The Stack Manifest (`k8s/deepseek-stack.yaml`)

**vLLM Deployment:**

```yaml
image: vllm/vllm-openai:latest
command: ["vllm", "serve", "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"]
args:
  - "--tensor-parallel-size=1"  # Single GPU - OOM on 5090 with TP=2
  - "--gpu-memory-utilization=0.95"
  - "--port=8000"
  - "--enforce-eager"           # Skip CUDA graphs (hang on Blackwell)
  - "--max-model-len=32768"     # 32K context
resources:
  limits:
    nvidia.com/gpu: 1
```

**MCP Gateway:**
- Serves filesystem and postgres over SSE/Stdio

**Command Module:**
- Ubuntu pod with persistent NVMe storage
