# Protocol OMNI v15.0 Deployment Status

**Date**: 2026-01-21  
**Authorization**: TITANIUM-PRIME-GO  
**Target**: Proxmox 192.168.3.10 → Talos k8s VM 192.168.3.2

## Infrastructure Summary

| Component | Status | Details |
|-----------|--------|---------|
| Proxmox Host | ✅ Ready | 192.168.3.10, GRUB params correct |
| Talos VM (105) | ✅ Running | 192.168.3.2, 300GB RAM, 96 CPUs |
| GPUs | ✅ Available | 2x NVIDIA (RTX PRO 6000 96GB + RTX 5090 32GB) |
| NVIDIA Plugin | ✅ Running | nvidia.com/gpu: 2 allocatable |
| NFS Storage | ✅ Configured | /nvme exported, PV/PVC bound |
| Control Plane Taint | ✅ Removed | Workloads can schedule |
| Models | ⏳ Downloading | Q3_K_M 319GB total, 180GB done (56%), ~70min ETA |
| Container Image | ✅ Ready | 192.168.3.10:5000/omni/ktransformers:v15 pushed |

## Corrections Applied

| Issue | Status | Implementation |
|-------|--------|----------------|
| GRUB Parameters | ✅ Done | `vfio_pci.disable_idle_d3=1 initcall_blacklist=sysfb_init` |
| Swap/OOM | ⚠️ Mitigated | Talos immutable; using strict memory limits + probes |
| VRAM Constraints | ✅ Done | GLM/MiniMax at replicas=0, documented in manifests |
| UFW Pod CIDR | ⚠️ N/A | Talos/k8s uses Flannel CNI, no UFW |

## Infrastructure Differences from Plan

| Plan | Actual | Impact |
|------|--------|--------|
| Bare metal Ubuntu 24.04 | Talos Linux VM | Uses NFS instead of local hostPath |
| k3s | k8s v1.35 (Talos) | Manifest compatible, no changes needed |
| Local /nvme | NFS from Proxmox host | 2.7TB available on ZFS |
| UFW firewall | Flannel CNI | NetworkPolicy works, no UFW needed |
| 64GB swap file | N/A | Talos is immutable, rely on kubelet OOM |

## Next Steps

### 1. Monitor Download Progress
```bash
# On Proxmox host (192.168.3.10)
watch -n 10 'du -sh /nvme/models/deepseek-v3.2-dq3/.cache/'
# Or check log
tail -f /root/download.log
```

### 2. After Download Complete - Apply Deployment
```bash
# After models are downloaded
kubectl apply -f k8s/zone-a-inference.yaml
```

### 3. Verify Deployment
```bash
kubectl get pods -n inference -w
curl http://192.168.3.2:8000/health
```

## Credentials

Stored securely outside repository. See system administrator for access.

## Files Created

- `k8s/zone-a-inference.yaml` - DeepSeek deployment (NFS volumes, Talos hostname)
- `k8s/zone-b-agents.yaml` - Agent orchestrator (gVisor)
- `k8s/network-policy.yaml` - Zone B egress restrictions
- `k8s/prometheus-alerts.yaml` - Memory/GPU alerts
- `docs/deployment/production-v15.md` - Full deployment guide

## Verification Checklist

| # | Check | Command | Status |
|---|-------|---------|--------|
| 1 | GRUB params | `cat /proc/cmdline` | ✅ Verified |
| 2 | GPUs visible | `kubectl describe nodes \| grep nvidia` | ✅ 2 GPUs |
| 3 | NFS mounts | Test pod completed | ✅ Working |
| 4 | Node schedulable | Taint removed | ✅ Done |
| 5 | Models downloaded | `ls /nvme/models/` | ⏳ Pending |
| 6 | Inference running | `curl :8000/health` | ⏳ Pending |
