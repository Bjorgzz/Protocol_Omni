# AI/LLM Inference Tuning - Quick Reference Card

**Last Updated:** 2026-01-30  
**Platform:** Threadripper PRO 9995WX + NVIDIA Blackwell

---

## Critical Settings (Apply First)

### 1. Disable AutoNUMA (NVIDIA Official - Blackwell Critical)
```bash
echo "kernel.numa_balancing = 0" >> /etc/sysctl.conf
sysctl -w kernel.numa_balancing=0
```
**Impact:** 10-20% performance improvement  
**Reason:** Prevents page fault storms on GPU workloads

### 2. Disable Transparent Huge Pages
```bash
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
```
**Impact:** 8-15% latency reduction  
**Reason:** Avoids THP allocation stalls

### 3. Enable nvidia-persistenced
```bash
systemctl enable --now nvidia-persistenced
nvidia-smi -pm 1
```
**Impact:** 200-500ms startup latency reduction  
**Reason:** Keeps GPU driver loaded

### 4. Disable PCIe ASPM (Set in BIOS)
```bash
# Verify in Linux:
lspci -vv | grep -i aspm
# Should show: L0s- L1-
```
**Impact:** 10-15% PCIe throughput improvement  
**Reason:** Eliminates PCIe power state transition latency

---

## Memory Settings

```bash
# /etc/sysctl.conf
vm.swappiness = 1                      # Minimal swapping
vm.nr_hugepages = 65536                # 128GB explicit huge pages (2MB each)
vm.compaction_proactiveness = 20       # Reduce fragmentation
vm.dirty_ratio = 10                    # Faster writeback
vm.dirty_background_ratio = 5
```

---

## Scheduler Settings

```bash
# /etc/sysctl.conf
kernel.sched_autogroup_enabled = 0     # Better thread scheduling for inference
```

---

## NVIDIA GPU Settings

```bash
# Persistence mode
nvidia-smi -pm 1

# Compute mode (per GPU)
nvidia-smi -i 0 -c EXCLUSIVE_PROCESS
nvidia-smi -i 1 -c EXCLUSIVE_PROCESS

# Power limits (adjust for your cooling)
nvidia-smi -i 0 -pl 600    # RTX PRO 6000
nvidia-smi -i 1 -pl 750    # RTX 5090 (liquid chilled)
```

---

## Docker Container Settings

```bash
# Single GPU with NUMA locality
docker run --gpus '"device=0"' \
  --cpuset-cpus="0-47" \
  --memory="192g" \
  --shm-size="16g" \
  your-inference-image

# Multi-GPU
docker run --gpus all \
  --shm-size="16g" \
  your-inference-image
```

**Critical:** `--shm-size="16g"` prevents IPC failures

---

## llama.cpp Optimizations

```bash
# CPU inference with huge pages
./llama-server \
  --mlock \
  --numa distribute \
  --model /models/model.gguf \
  --ctx-size 32768

# Multi-GPU inference
CUDA_VISIBLE_DEVICES=0,1 ./llama-server \
  --model /models/model.gguf \
  --tensor-split 3,1 \
  --ctx-size 32768
```

---

## Verification Commands

```bash
# Memory
cat /sys/kernel/mm/transparent_hugepage/enabled  # Should show: [never]
sysctl vm.swappiness                              # Should show: 1
grep HugePages_Total /proc/meminfo                # Should show: 65536

# NUMA
sysctl kernel.numa_balancing                      # Should show: 0
numactl --hardware                                # Check node count

# NVIDIA
nvidia-smi -q | grep "Persistence Mode"           # Should show: Enabled
nvidia-smi topo -m                                # Check P2P topology

# PCIe ASPM
lspci -vv | grep -i aspm | head -1               # Should show: L0s- L1-
```

---

## Performance Targets

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Token/s Generation | 11.35 | 13.5-15 | `llama-bench` |
| Token/s Prompt | 23.14 | 28-32 | `llama-bench` |
| Memory BW | ~350 GB/s | >420 GB/s | STREAM Triad |
| GPU P2P Latency | SYS (10μs) | PHB (1-2μs) | `nvidia-smi topo` |

---

## One-Line Tuning Script

```bash
# Download and execute (review first!)
curl -fsSL https://raw.githubusercontent.com/.../tune-ai-inference.sh | sudo bash

# Or from local repo
sudo /path/to/Protocol_Omni/scripts/tune-ai-inference.sh
```

---

## Emergency Rollback

```bash
# Restore sysctl settings
sudo cp /root/sysctl-backup-YYYYMMDD-HHMMSS.conf /etc/sysctl.conf
sudo sysctl -p

# Re-enable THP (if needed)
echo always > /sys/kernel/mm/transparent_hugepage/enabled

# Reset NVIDIA settings
nvidia-smi -pm 0
nvidia-smi -c DEFAULT
```

---

## References

- **Full Documentation:** `docs/operations/linux-kernel-tuning-ai-inference.md`
- **BIOS Tuning:** `docs/plans/2026-01-29-operation-velocity-extreme-ai.md`
- **Verification Script:** `scripts/verify-ai-tuning.sh`
- **NVIDIA Official:** https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/

---

## Expected Overall Impact

**Multi-GPU LLM Inference:** 15-30% throughput improvement  
**Single-GPU Inference:** 10-20% throughput improvement  
**Startup Latency:** 200-500ms reduction  
**Stability:** Significant improvement under sustained load

---

*Quick reference for Protocol Omni AI inference optimization*
