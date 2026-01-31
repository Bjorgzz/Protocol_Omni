#!/bin/bash
#
# AI/LLM Inference Tuning Verification Script
# Verifies all OS-level and NVIDIA settings for optimal inference performance
#
# Usage: sudo ./verify-ai-tuning.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

echo "============================================"
echo "  AI/LLM Inference Tuning Verification"
echo "  $(date)"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    check_warn "Not running as root - some checks may fail"
    echo ""
fi

#
# MEMORY MANAGEMENT
#
echo "=== MEMORY MANAGEMENT ==="

# Transparent Huge Pages
THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null)
if [[ "$THP" == *"[never]"* ]]; then
    check_pass "THP disabled: $THP"
elif [[ "$THP" == *"[madvise]"* ]]; then
    check_warn "THP set to madvise (acceptable for kernel 6.9+)"
else
    check_fail "THP enabled (should be 'never' or 'madvise'): $THP"
fi

# Huge Pages
HP_TOTAL=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
HP_FREE=$(grep HugePages_Free /proc/meminfo | awk '{print $2}')
if [ "$HP_TOTAL" -gt 0 ]; then
    check_pass "Huge pages allocated: $HP_TOTAL total, $HP_FREE free"
else
    check_warn "No huge pages allocated (optional but recommended)"
fi

# vm.swappiness
SWAPPINESS=$(sysctl -n vm.swappiness)
if [ "$SWAPPINESS" -le 10 ]; then
    check_pass "vm.swappiness = $SWAPPINESS (optimal: ≤10)"
else
    check_warn "vm.swappiness = $SWAPPINESS (recommend: 1-10)"
fi

# AutoNUMA
NUMA_BAL=$(sysctl -n kernel.numa_balancing)
if [ "$NUMA_BAL" -eq 0 ]; then
    check_pass "AutoNUMA disabled (NVIDIA recommendation)"
else
    check_fail "AutoNUMA enabled (should be disabled for Blackwell)"
fi

# Memory compaction
COMPACT=$(sysctl -n vm.compaction_proactiveness)
if [ "$COMPACT" -ge 20 ]; then
    check_pass "vm.compaction_proactiveness = $COMPACT"
else
    check_warn "vm.compaction_proactiveness = $COMPACT (recommend: 20)"
fi

# Dirty ratios
DIRTY_RATIO=$(sysctl -n vm.dirty_ratio)
DIRTY_BG=$(sysctl -n vm.dirty_background_ratio)
if [ "$DIRTY_RATIO" -le 15 ] && [ "$DIRTY_BG" -le 10 ]; then
    check_pass "Dirty ratios: ratio=$DIRTY_RATIO, bg_ratio=$DIRTY_BG"
else
    check_warn "Dirty ratios: ratio=$DIRTY_RATIO, bg_ratio=$DIRTY_BG (recommend: 10/5)"
fi

echo ""

#
# SCHEDULER
#
echo "=== SCHEDULER ==="

# sched_autogroup
AUTOGROUP=$(sysctl -n kernel.sched_autogroup_enabled)
if [ "$AUTOGROUP" -eq 0 ]; then
    check_pass "sched_autogroup disabled"
else
    check_warn "sched_autogroup enabled (recommend: disabled for inference)"
fi

# IRQ balance
if systemctl is-active --quiet irqbalance; then
    check_pass "irqbalance service running"
else
    check_warn "irqbalance service not running (acceptable if using CPU isolation)"
fi

echo ""

#
# NUMA TOPOLOGY
#
echo "=== NUMA TOPOLOGY ==="
NUMA_NODES=$(numactl --hardware 2>/dev/null | grep "available:" | awk '{print $2}')
if [ -n "$NUMA_NODES" ]; then
    if [ "$NUMA_NODES" -eq 1 ]; then
        check_pass "NUMA nodes: $NUMA_NODES (optimal - NPS1 configured)"
    else
        check_warn "NUMA nodes: $NUMA_NODES (consider NPS1 for inference)"
    fi
    numactl --hardware | head -5
else
    check_warn "Unable to read NUMA topology"
fi

echo ""

#
# NVIDIA
#
echo "=== NVIDIA ==="

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    check_fail "nvidia-smi not found - NVIDIA drivers not installed?"
    exit 1
fi

# Persistence mode
PERSIST=$(nvidia-smi -q 2>/dev/null | grep "Persistence Mode" | head -1 | awk '{print $4}')
if [ "$PERSIST" == "Enabled" ]; then
    check_pass "GPU Persistence Mode: Enabled"
else
    check_fail "GPU Persistence Mode: $PERSIST (should be Enabled)"
fi

# nvidia-persistenced service
if systemctl is-active --quiet nvidia-persistenced 2>/dev/null; then
    check_pass "nvidia-persistenced service running"
else
    check_warn "nvidia-persistenced service not running"
fi

# Compute mode
COMPUTE_MODE=$(nvidia-smi -q 2>/dev/null | grep "Compute Mode" | head -1 | awk '{print $4}')
if [ "$COMPUTE_MODE" == "Exclusive_Process" ]; then
    check_pass "GPU Compute Mode: $COMPUTE_MODE"
else
    check_warn "GPU Compute Mode: $COMPUTE_MODE (recommend: Exclusive_Process)"
fi

# Power limits
echo ""
echo "GPU Power Configuration:"
nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader | while IFS=',' read -r idx name power; do
    echo "  GPU $idx ($name): $power"
done

# GPU count
GPU_COUNT=$(nvidia-smi -L | wc -l)
check_pass "Detected GPUs: $GPU_COUNT"

# GPU topology (P2P)
echo ""
echo "GPU Topology (P2P Capabilities):"
nvidia-smi topo -m 2>/dev/null | head -8

echo ""

#
# PCIE
#
echo "=== PCIe ==="

# ASPM status
if command -v lspci &> /dev/null; then
    ASPM_LINE=$(lspci -vv 2>/dev/null | grep -i "lnkctl:" | grep -i aspm | head -1)
    if [[ "$ASPM_LINE" == *"L0s- L1-"* ]] || [[ "$ASPM_LINE" == *"Disabled"* ]]; then
        check_pass "ASPM disabled (optimal for inference)"
    else
        check_warn "ASPM status unclear: $ASPM_LINE"
    fi
else
    check_warn "lspci not available - cannot verify ASPM"
fi

# Check kernel command line for pcie_aspm
CMDLINE=$(cat /proc/cmdline)
if [[ "$CMDLINE" == *"pcie_aspm=off"* ]]; then
    check_pass "Kernel parameter: pcie_aspm=off"
fi

echo ""

#
# NETWORK
#
echo "=== NETWORK ==="

BUSY_POLL=$(sysctl -n net.core.busy_poll 2>/dev/null)
BUSY_READ=$(sysctl -n net.core.busy_read 2>/dev/null)
if [ "$BUSY_POLL" -ge 50 ] && [ "$BUSY_READ" -ge 50 ]; then
    check_pass "Network busy polling enabled: poll=$BUSY_POLL, read=$BUSY_READ"
else
    check_warn "Network busy polling: poll=$BUSY_POLL, read=$BUSY_READ (recommend: 50)"
fi

RMEM=$(sysctl -n net.core.rmem_max 2>/dev/null)
WMEM=$(sysctl -n net.core.wmem_max 2>/dev/null)
if [ "$RMEM" -ge 134217728 ] && [ "$WMEM" -ge 134217728 ]; then
    check_pass "Network buffers: rmem=$RMEM, wmem=$WMEM"
else
    check_warn "Network buffers: rmem=$RMEM, wmem=$WMEM (recommend: 134217728)"
fi

echo ""

#
# DOCKER (if available)
#
echo "=== DOCKER ==="

if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        check_pass "Docker installed and running"
        
        # Check nvidia-docker runtime
        if docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
            check_pass "NVIDIA Docker runtime functional"
        else
            check_warn "NVIDIA Docker runtime not working"
        fi
    else
        check_warn "Docker installed but not running"
    fi
else
    check_warn "Docker not installed"
fi

echo ""

#
# SUMMARY
#
echo "============================================"
echo "  Verification Complete"
echo "============================================"
echo ""
echo "Review any warnings (⚠) or failures (✗) above."
echo "For optimal inference performance, all checks should pass (✓)."
echo ""
echo "Configuration files:"
echo "  - Kernel parameters: /etc/sysctl.conf"
echo "  - NVIDIA persistence: /etc/systemd/system/nvidia-power-limit.service"
echo "  - Boot parameters: /etc/default/grub"
echo ""
echo "Documentation:"
echo "  - Linux tuning guide: docs/operations/linux-kernel-tuning-ai-inference.md"
echo "  - BIOS tuning: docs/plans/2026-01-29-operation-velocity-extreme-ai.md"
echo ""
