# Operation Leviathan: Full Stack Deployment

## Objective
Mount the 4TB NVMe on Talos node, download DeepSeek-V3 GGUF weights, and build the Leviathan inference engine with KTransformers on the verified Blackwell-compatible base image.

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Phase 1: Storage Setup"
        A[Sysadmin Pod] -->|privileged| B[/dev/nvme0n1]
        B -->|mkfs.xfs| C[Mount to /var/mnt/data]
        C -->|Bidirectional Propagation| D[Host sees mount]
    end
    
    subgraph "Phase 2: Model Download"
        D --> E[huggingface-cli download]
        E --> F[/data/models/deepseek-v3-gguf]
    end
    
    subgraph "Phase 3: Engine Build"
        G[bleeding-edge-v2] -->|FROM| H[Leviathan Dockerfile]
        H -->|git clone ktransformers| I[Build with TORCH_CUDA_ARCH_LIST]
        I --> J[omni/engine:leviathan-blackwell]
    end
    
    subgraph "Phase 4: Deployment"
        J --> K[Inference Pod]
        F -->|hostPath mount| K
        K --> L[API Service :30000]
    end
```

---

## Phase 1: Sysadmin Logistics Pod

**File:** `manifests/sysadmin-logistics.yaml`

**Actions:**
1. Create the manifest file with privileged pod spec
2. Apply to cluster
3. Monitor logs for NVMe detection and mount confirmation

**Key Configuration:**
- `privileged: true` - Required for device formatting
- `mountPropagation: Bidirectional` - Ensures host sees the mount
- `hostPath: /var/mnt/data` with `DirectoryOrCreate`
- `nodeName: talos-node-0` - Pin to GPU node

**Verification:**
```bash
kubectl logs -n ai-workloads sysadmin-logistics -f
# Expect: ">> MOUNTING /dev/nvme0n1 to /data..."
# Expect: ">> DOWNLOAD COMPLETE. READY FOR LEVIATHAN."
```

**Risk:** NVMe device name may differ. Will check `lsblk` output in logs first.

---

## Phase 2: Model Download (Runs Inside Phase 1 Pod)

**Model:** `unsloth/DeepSeek-V3-GGUF` (Q4_K_M quantization)

**Download Location:** `/data/models/deepseek-v3-gguf` (maps to host `/var/mnt/data/models/deepseek-v3-gguf`)

**Expected Size:** ~100-150GB for Q4_K_M shards

**Monitoring:**
```bash
kubectl exec -n ai-workloads sysadmin-logistics -- ls -lah /data/models/deepseek-v3-gguf/
```

---

## Phase 3: Leviathan Engine Build (Parallel with Phase 2)

**File:** `/root/docker/Dockerfile.leviathan` on Proxmox

**Base Image:** `192.168.3.10:5000/omni/engine:bleeding-edge-v2` (verified working)

**Key Build Variables:**
- `TORCH_CUDA_ARCH_LIST="9.0a 10.0"` - Enables Hopper + Blackwell compute paths
- `ENABLE_DEEPGEMM=1` - Activates DeepSeek optimized GEMM kernels

**Build Command:**
```bash
docker build --network host -t omni/engine:leviathan-blackwell \
  -f /root/docker/Dockerfile.leviathan /root/docker/
```

**Push Command:**
```bash
docker tag omni/engine:leviathan-blackwell 192.168.3.10:5000/omni/engine:leviathan-blackwell
docker push 192.168.3.10:5000/omni/engine:leviathan-blackwell
```

---

## Phase 4: Deployment Manifest Update

**File:** `k8s/bleeding-edge-deploy.yaml` or new `manifests/leviathan-deploy.yaml`

**Changes:**
- Image: `192.168.3.10:5000/omni/engine:leviathan-blackwell`
- Volume path: `/var/mnt/data/models/deepseek-v3-gguf`
- Entrypoint: `python3 -m ktransformers.server.main`
- Model args for KTransformers CLI

---

## Execution Sequence

| Step | Action | Blocking? | Verification |
|------|--------|-----------|--------------|
| 1.1 | Create `manifests/sysadmin-logistics.yaml` | No | File exists |
| 1.2 | Apply sysadmin pod | Yes | Pod Running |
| 1.3 | Verify NVMe mount in logs | Yes | "MOUNTING" message |
| 2.1 | Monitor download progress | No | Files appearing in `/data/models/` |
| 3.1 | Create `Dockerfile.leviathan` on Proxmox | No | File exists |
| 3.2 | Build Leviathan image | Yes | Build completes |
| 3.3 | Push to registry | Yes | Tag visible in registry |
| 4.1 | Create/update deployment manifest | No | File ready |
| 4.2 | Apply deployment (after 2.1 + 3.3 complete) | Yes | Pod Running |
| 4.3 | Verify inference endpoint | - | `curl :30000/health` returns OK |

---

## Definition of Done

- [ ] NVMe mounted at `/var/mnt/data` on Talos host
- [ ] DeepSeek-V3 GGUF weights downloaded to `/var/mnt/data/models/deepseek-v3-gguf`
- [ ] `omni/engine:leviathan-blackwell` image in local registry
- [ ] Inference pod running and serving requests on port 30000

---

## Constraints & Risks

| Risk | Mitigation |
|------|------------|
| NVMe device name differs | Check `lsblk` in pod logs before formatting |
| Download interrupted | HuggingFace CLI supports resume |
| KTransformers build fails | Fall back to vLLM with GGUF loader |
| Mount not visible to host | Verify `mountPropagation: Bidirectional` is respected |
