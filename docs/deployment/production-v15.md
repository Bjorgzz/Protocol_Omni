# Protocol OMNI v15.0 Production Deployment Guide

> **Version**: v15.0 "SOVEREIGN SPLIT"  
> **Status**: Production Ready  
> **Last Updated**: 2025-01-22

## Overview

This guide covers the complete production deployment of Protocol OMNI v15.0 with Zone A/B security isolation on bare metal Ubuntu 24.04.

## Critical Corrections Applied

| Issue | Fix | Impact |
|-------|-----|--------|
| GRUB Regression | Added `vfio_pci.disable_idle_d3=1 initcall_blacklist=sysfb_init` | Prevents Blackwell FLR Reset Bug |
| OOM Risk | 64GB NVMe swap file | Prevents OOM Killer terminating KTransformers |
| VRAM Hallucination | GLM→CPU-only, MiniMax→Cold Storage | Avoids VRAM exhaustion |
| Firewall Blackout | UFW Pod CIDR exceptions | Enables Zone B→A communication |

## Hardware Requirements

| Component | Specification | Verification |
|-----------|---------------|--------------|
| CPU | Threadripper 9995WX (96 cores, AVX-512) | `lscpu \| grep avx512` |
| RAM | 384GB DDR5-6400 ECC | `free -h` |
| GPU 0 | RTX PRO 6000 Blackwell (96GB) | `nvidia-smi` |
| GPU 1 | RTX 5090 (32GB) | `nvidia-smi` |
| Storage | 2× 4TB NVMe Gen5 | `lsblk` |
| Network | Ubuntu 24.04 @ 192.168.3.10 | `ip a` |

### BIOS Settings (Critical)

| Setting | Value | Why |
|---------|-------|-----|
| NPS | 4 | 4 NUMA nodes for 384GB access |
| PCIe Link Speed | Gen5 | Full GPU bandwidth |
| IOMMU | Enabled | Container GPU passthrough |

## Memory Budget

| Component | RAM Usage |
|-----------|-----------|
| DeepSeek-V3.2 (DQ3_K_M) | ~281 GB |
| KV Cache (max context) | ~60 GB |
| Agents + OS + Buffers | ~20 GB |
| **Total** | **~361 GB (94%)** |
| **Available** | 384 GB |
| **Safety Buffer (Swap)** | 64 GB NVMe |

> **Physics**: Running at 94% utilization. The 64GB swap file prevents OOM Killer from terminating KTransformers on memory spikes.

---

## Phase 1: Base System Preparation

### 1.1 Kernel Parameters

Edit `/etc/default/grub`:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash pcie_aspm=off iommu=pt amd_iommu=on vfio_pci.disable_idle_d3=1 initcall_blacklist=sysfb_init"
```

| Parameter | Purpose |
|-----------|---------|
| `pcie_aspm=off` | Disable PCIe power saving (stability) |
| `iommu=pt` | Passthrough mode for GPU |
| `amd_iommu=on` | Enable AMD IOMMU |
| `vfio_pci.disable_idle_d3=1` | **CRITICAL**: Prevents RTX 5090 sleep state → FLR Reset Bug |
| `initcall_blacklist=sysfb_init` | **CRITICAL**: Prevents boot splash VRAM lock |

Apply:

```bash
sudo update-grub
sudo reboot
```

Verify:

```bash
cat /proc/cmdline | grep -E "vfio_pci.disable_idle_d3|initcall_blacklist"
```

### 1.2 Storage Setup + Swap

```bash
# Create directory structure
sudo mkdir -p /nvme/{models,prompts,mem0,letta,memgraph,qdrant,prometheus,grafana,phoenix,gepa,agent,eval}
sudo chown -R $USER:$USER /nvme

# CREATE 64GB SWAP FILE (OOM PROTECTION)
sudo fallocate -l 64G /nvme/swapfile
sudo chmod 600 /nvme/swapfile
sudo mkswap /nvme/swapfile
sudo swapon /nvme/swapfile
echo '/nvme/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
swapon --show
```

### 1.3 Model Download

```bash
pip install huggingface-cli

# DeepSeek-V3.2 DQ3_K_M (~281GB)
huggingface-cli download unsloth/DeepSeek-V3.2-GGUF \
  --include "*DQ3_K_M*" \
  --local-dir /nvme/models/deepseek-v3.2-dq3
```

---

## Phase 2: k3s Production Deployment

### 2.1 Install k3s + gVisor

```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --disable servicelb \
  --write-kubeconfig-mode 644

# Install gVisor
sudo apt install -y runsc
sudo mv /usr/bin/runsc /usr/local/bin/

# Configure containerd for gVisor
cat <<EOF | sudo tee /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.gvisor]
  runtime_type = "io.containerd.runsc.v1"
EOF

# Create RuntimeClass
kubectl apply -f - <<EOF
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: gvisor
EOF

sudo systemctl restart k3s
```

### 2.2 Install NVIDIA Device Plugin

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/deployments/static/nvidia-device-plugin.yml
```

### 2.3 Deploy Zone A (Inference)

```bash
kubectl apply -f k8s/zone-a-inference.yaml
```

Key configurations:
- `restartPolicy: OnFailure` (Blackwell reset bug mitigation)
- `startupProbe: 300s initial, 40 failures` (25 min tolerance for 281GB load)
- `livenessProbe: 600s initial, 10 failures`
- NUMA: `numactl --cpunodebind=0 --interleave=all`

### 2.4 Deploy Zone B (Agents)

```bash
kubectl apply -f k8s/zone-b-agents.yaml
```

Key configurations:
- `runtimeClassName: gvisor`
- All endpoints target `192.168.3.10` (NOT localhost)
- `capabilities: drop: ALL`

### 2.5 Deploy Network Policies

```bash
kubectl apply -f k8s/network-policy.yaml
```

### 2.6 Deploy Memory + Observability

```bash
cd ~/Protocol_Omni/docker
docker compose -f memory-stack.yaml up -d
docker compose -f observability-stack.yaml up -d
```

---

## Phase 3: Security Configuration

### 3.1 Firewall (UFW)

```bash
sudo ufw allow ssh
sudo ufw allow 8000:8100/tcp   # Inference APIs
sudo ufw allow 3000/tcp        # Grafana
sudo ufw allow 9090/tcp        # Prometheus

# CRITICAL: Allow k3s Pod/Service traffic
sudo ufw allow from 10.42.0.0/16 to any  # Pod CIDR
sudo ufw allow from 10.43.0.0/16 to any  # Service CIDR

sudo ufw enable
```

Verify:

```bash
sudo ufw status | grep -E "10.42|10.43"
```

---

## Phase 4: Verification

### Pre-Flight Checks

```bash
# GRUB parameters
cat /proc/cmdline | grep -E "vfio_pci.disable_idle_d3|initcall_blacklist"

# Swap active
swapon --show

# UFW rules
sudo ufw status | grep 10.42
```

### Health Checks

```bash
# Zone A - Inference
curl http://192.168.3.10:8000/health
curl http://192.168.3.10:8000/v1/models

# Zone B - Agents
kubectl exec -n agents deploy/agent-orchestrator -- curl http://192.168.3.10:8000/health

# Memory Services
curl http://192.168.3.10:8050/health  # Mem0
curl http://192.168.3.10:8283/health  # Letta
curl http://192.168.3.10:6333/health  # Qdrant
```

### NUMA Verification

```bash
numastat -p $(pgrep -f ktransformers)
# Expected: Memory spread across all 4 nodes (~70GB each)
```

### Inference Test

```bash
curl -X POST http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "Hello"}]}'
```

### gVisor Isolation

```bash
kubectl exec -n agents deploy/agent-orchestrator -- cat /proc/version
# Should show gVisor kernel, NOT host kernel
```

---

## Definition of Done

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | GRUB params | `cat /proc/cmdline` | `disable_idle_d3=1`, `sysfb_init` present |
| 2 | Swap active | `swapon --show` | 64GB on `/nvme/swapfile` |
| 3 | UFW Pod CIDR | `sudo ufw status` | 10.42.0.0/16, 10.43.0.0/16 ALLOW |
| 4 | GPU visible | `nvidia-smi` | 2 GPUs, 128GB total |
| 5 | Model loaded | `curl :8000/v1/models` | DeepSeek-V3.2 listed |
| 6 | NUMA correct | `numastat -p $(pgrep ktransformers)` | 4 nodes, ~70GB each |
| 7 | Zone B isolated | `kubectl exec ... cat /proc/version` | gVisor kernel |
| 8 | Inference works | `curl :8000/v1/chat/completions` | 200 OK, ~20 tok/s |
| 9 | Zone B→A route | `kubectl exec ... curl 192.168.3.10:8000/health` | 200 OK |
| 10 | No restart loops | `kubectl get pods -w` (10 min) | Stays Running |

---

## Services Summary

| Service | Port | Zone | Status | Notes |
|---------|------|------|--------|-------|
| DeepSeek-V3.2 | 8000 | A | **Active** | GPU0: 90GB + GPU1: 30GB |
| GLM-4.7 | 8002 | A | **CPU-Only** | No GPU - VRAM exhausted |
| MiniMax | 8003 | - | **Cold Storage** | replicas=0, emergency only |
| Metacognition | 8011 | B | Active | gVisor sandbox |
| Agent Orchestrator | 8080 | B | Active | gVisor sandbox |
| Mem0 | 8050 | - | Active | Docker Compose |
| Letta | 8283 | - | Active | Docker Compose |
| Qdrant | 6333 | - | Active | Docker Compose |
| Memgraph | 7687 | - | Active | Docker Compose |
| Prometheus | 9090 | - | Active | Docker Compose |
| Grafana | 3000 | - | Active | Docker Compose |

---

## Rollback

```bash
# k3s
kubectl delete -f k8s/zone-a-inference.yaml
kubectl delete -f k8s/zone-b-agents.yaml

# Docker Compose
docker compose -f omni-stack.yaml down
docker compose -f memory-stack.yaml down
docker compose -f observability-stack.yaml down

# Disable swap
sudo swapoff /nvme/swapfile
sudo sed -i '/swapfile/d' /etc/fstab
```

---

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Operational doctrine
- [Architecture Overview](../architecture/overview.md)
- [Zone Security](../architecture/zone-security.md)
- [Monitoring](../operations/monitoring.md)
- [Troubleshooting](../operations/troubleshooting.md)
