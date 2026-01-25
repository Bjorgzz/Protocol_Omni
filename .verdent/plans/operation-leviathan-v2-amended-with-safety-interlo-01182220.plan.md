# Operation Leviathan v2: Final Execution Plan

## Critical Amendments Incorporated

| Amendment | Impact |
|-----------|--------|
| Dynamic Disk Finder | Prevents OS wipe - only formats drives > 3.5TB |
| DeepGEMM Pre-install | Ensures FP8 kernels link correctly with KTransformers |
| NUMA Interleaving | Unlocks 300GB/s DDR5 bandwidth across 8 channels |
| GPU Split | 90GB RTX 6000 + 30GB RTX 5090 + ~260GB RAM spillover |
| Model Size Correction | 385GB total (not 150GB) |

---

## Phase 1: Sysadmin Logistics Pod

**File:** `manifests/sysadmin-logistics.yaml`

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sysadmin-logistics
  namespace: ai-workloads
spec:
  restartPolicy: Never
  nodeName: talos-node-0
  containers:
  - name: admin
    image: ubuntu:22.04
    securityContext:
      privileged: true
    command: ["/bin/bash", "-c"]
    args:
      - |
        apt-get update && apt-get install -y python3-pip wget git xfsprogs curl numactl
        pip install huggingface_hub[cli]
        
        echo ">> SEARCHING FOR 4TB NVME..."
        
        # SAFETY INTERLOCK: DYNAMIC DISK FINDER
        TARGET_DISK=$(lsblk -bdn -o NAME,SIZE -p | awk '$2 > 3500000000000 {print $1}' | head -n 1)

        if [ -z "$TARGET_DISK" ]; then
            echo "!!!! CRITICAL ABORT: 4TB NVME NOT FOUND."
            echo "!!!! DUMPING BLOCK DEVICES FOR REVIEW:"
            lsblk
            exit 1
        fi

        echo ">> TARGET ACQUIRED: $TARGET_DISK"

        if ! mountpoint -q /data; then
             echo ">> MOUNTING $TARGET_DISK to /data..."
             if ! blkid $TARGET_DISK; then
                 echo ">> NO FILESYSTEM DETECTED. FORMATTING..."
                 mkfs.xfs -f $TARGET_DISK
             fi
             mkdir -p /data
             mount $TARGET_DISK /data
        fi
        
        echo ">> STARTING DOWNLOAD OF DEEPSEEK-V3 (Q4_K_M) - ~385GB..."
        mkdir -p /data/models/deepseek-v3-gguf
        
        huggingface-cli download unsloth/DeepSeek-V3-GGUF \
          --include "*Q4_K_M*" \
          --local-dir /data/models/deepseek-v3-gguf \
          --local-dir-use-symlinks False
          
        echo ">> DOWNLOAD COMPLETE. READY FOR LEVIATHAN."
        sleep infinity
    volumeMounts:
    - name: host-mount-point
      mountPath: /data
      mountPropagation: Bidirectional
  volumes:
  - name: host-mount-point
    hostPath:
      path: /var/mnt/data
      type: DirectoryOrCreate
```

---

## Phase 3: Leviathan Dockerfile

**File:** `/root/docker/Dockerfile.leviathan` on Proxmox

```dockerfile
FROM 192.168.3.10:5000/omni/engine:bleeding-edge-v2

ENV TORCH_CUDA_ARCH_LIST="9.0a 10.0"
ENV ENABLE_DEEPGEMM=1

# 1. INSTALL DEEPGEMM FIRST (CRITICAL for FP8 kernel linking)
WORKDIR /opt
RUN git clone https://github.com/deepseek-ai/DeepGEMM.git \
    && cd DeepGEMM && python3 setup.py install

# 2. CLONE AND BUILD KTRANSFORMERS
WORKDIR /app
RUN git clone https://github.com/kvcache-ai/ktransformers.git . \
    && git submodule update --init --recursive

RUN pip3 install -r requirements.txt --break-system-packages
RUN pip3 install . --break-system-packages

# Install numactl for memory striping
RUN apt-get update && apt-get install -y numactl && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash", "-c"]
```

---

## Phase 4: Leviathan Deployment

**File:** `manifests/leviathan-deploy.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: leviathan-inference
  namespace: ai-workloads
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: leviathan-inference
  template:
    metadata:
      labels:
        app: leviathan-inference
    spec:
      runtimeClassName: nvidia
      nodeName: talos-node-0
      tolerations:
        - key: "node-role.kubernetes.io/control-plane"
          operator: "Exists"
          effect: "NoSchedule"
      containers:
        - name: inference-engine
          image: 192.168.3.10:5000/omni/engine:leviathan-blackwell
          imagePullPolicy: Always
          command: ["/bin/bash", "-c"]
          args:
            - |
              echo "Summoning Leviathan..."
              numactl --interleave=all \
              python3 -m ktransformers.server.main \
              --model_path /models/deepseek-v3-gguf \
              --model_name deepseek-v3 \
              --host 0.0.0.0 \
              --port 30000 \
              --cpu_offload_max_threads 96 \
              --gpu_split "90000,30000"
          env:
            - name: CUDA_VISIBLE_DEVICES
              value: "0,1"
          ports:
            - containerPort: 30000
          resources:
            limits:
              nvidia.com/gpu: "2"
              memory: "384Gi"
              cpu: "96"
          volumeMounts:
            - name: model-storage
              mountPath: /models
            - name: shm
              mountPath: /dev/shm
      volumes:
        - name: model-storage
          hostPath:
            path: /var/mnt/data/models
            type: Directory
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 64Gi
```

---

## Execution Sequence

| Step | Action | Verification |
|------|--------|--------------|
| 1.1 | Create `manifests/sysadmin-logistics.yaml` | File exists |
| 1.2 | `kubectl apply -f manifests/sysadmin-logistics.yaml` | Pod Running |
| 1.3 | Monitor logs for "TARGET ACQUIRED" | NVMe detected safely |
| 2.1 | Monitor download (~385GB) | Files in `/data/models/` |
| 3.1 | Create `Dockerfile.leviathan` on Proxmox | File exists |
| 3.2 | Build image (parallel with download) | Build completes |
| 3.3 | Push to registry | Tag in registry |
| 4.1 | Delete sysadmin pod after download | Pod deleted |
| 4.2 | Apply Leviathan deployment | Pod Running |
| 4.3 | `curl <node-ip>:30000/health` | Returns OK |

---

## Definition of Done

- [ ] NVMe > 3.5TB detected and mounted at `/var/mnt/data`
- [ ] DeepSeek-V3 GGUF (385GB) downloaded
- [ ] `omni/engine:leviathan-blackwell` in registry with DeepGEMM + KTransformers
- [ ] Inference pod running with NUMA interleaving and GPU split active
- [ ] `/health` endpoint responding

---

## GPU Memory Allocation

```
┌─────────────────────────────────────────────────────────────┐
│ RTX PRO 6000 Blackwell (96GB)                               │
│ ├── Context Window + Attention Heads: 90GB                  │
│ └── Reserved: 6GB                                           │
├─────────────────────────────────────────────────────────────┤
│ RTX 5090 (32GB)                                             │
│ ├── Hot Experts: 30GB                                       │
│ └── Reserved: 2GB                                           │
├─────────────────────────────────────────────────────────────┤
│ DDR5 RAM (384GB @ 300GB/s via NUMA interleave)              │
│ └── Cold Experts + KV Cache Spillover: ~260GB               │
└─────────────────────────────────────────────────────────────┘
```
