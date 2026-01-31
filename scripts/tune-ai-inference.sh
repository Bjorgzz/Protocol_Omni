#!/bin/bash
#
# AI/LLM Inference OS Tuning Script
# Optimizes Linux kernel parameters for AI/LLM inference workloads
#
# Target: Threadripper PRO 9995WX + NVIDIA Blackwell (RTX PRO 6000 + RTX 5090)
# Usage: sudo ./tune-ai-inference.sh
#
# Based on:
# - NVIDIA Grace Performance Tuning Guide
# - NVIDIA Blackwell Tuning Guide
# - Production LLM inference best practices (2026)
#

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    echo "Usage: sudo $0"
    exit 1
fi

echo "============================================"
echo "  AI/LLM Inference OS Tuning Script"
echo "  For: Threadripper PRO + NVIDIA Blackwell"
echo "  $(date)"
echo "============================================"
echo ""

# Backup current settings
BACKUP_FILE="/root/sysctl-backup-$(date +%Y%m%d-%H%M%S).conf"
echo "Backing up current sysctl settings to: $BACKUP_FILE"
sysctl -a > "$BACKUP_FILE" 2>/dev/null
echo ""

#
# MEMORY MANAGEMENT
#
echo "=== 1. MEMORY MANAGEMENT ==="

# Disable Transparent Huge Pages (THP)
# NVIDIA recommendation for Blackwell/Grace systems
echo "Disabling Transparent Huge Pages (THP)..."
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
echo "  ✓ THP disabled"

# Configure explicit huge pages (2MB pages)
# Calculate: 128GB / 2MB = 65536 pages
echo "Configuring explicit huge pages (128GB = 65536 x 2MB)..."
echo 65536 > /proc/sys/vm/nr_hugepages
ACTUAL_HP=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
echo "  ✓ Allocated $ACTUAL_HP huge pages"
if [ "$ACTUAL_HP" -lt 65536 ]; then
    echo "  ⚠ Warning: Requested 65536 but only got $ACTUAL_HP (memory fragmentation?)"
fi

# Set vm.swappiness
# Value: 1 = minimal swapping, keeps models in RAM
echo "Setting vm.swappiness = 1..."
sysctl -w vm.swappiness=1 > /dev/null
echo "  ✓ vm.swappiness = 1"

# Configure dirty page ratios
# Aggressive writeback for faster model loading
echo "Configuring dirty page writeback..."
sysctl -w vm.dirty_ratio=10 > /dev/null
sysctl -w vm.dirty_background_ratio=5 > /dev/null
echo "  ✓ vm.dirty_ratio = 10"
echo "  ✓ vm.dirty_background_ratio = 5"

# Enable proactive memory compaction
# Reduces fragmentation, improves huge page allocation
echo "Enabling proactive memory compaction..."
sysctl -w vm.compaction_proactiveness=20 > /dev/null
echo "  ✓ vm.compaction_proactiveness = 20"

# Disable AutoNUMA
# NVIDIA official recommendation: prevents page fault storms on Blackwell/Grace
echo "Disabling AutoNUMA (NVIDIA recommendation for Blackwell)..."
sysctl -w kernel.numa_balancing=0 > /dev/null
echo "  ✓ kernel.numa_balancing = 0"

echo ""

#
# SCHEDULER SETTINGS
#
echo "=== 2. SCHEDULER SETTINGS ==="

# Disable sched_autogroup
# Prevents automatic task grouping that can interfere with inference threads
echo "Disabling sched_autogroup..."
sysctl -w kernel.sched_autogroup_enabled=0 > /dev/null
echo "  ✓ kernel.sched_autogroup_enabled = 0"

echo ""

#
# NVIDIA SETTINGS
#
echo "=== 3. NVIDIA SETTINGS ==="

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "  ⚠ WARNING: nvidia-smi not found - skipping NVIDIA configuration"
    echo "  Please install NVIDIA drivers first"
else
    # Enable nvidia-persistenced service
    echo "Enabling nvidia-persistenced service..."
    if systemctl enable nvidia-persistenced 2>/dev/null; then
        systemctl start nvidia-persistenced
        echo "  ✓ nvidia-persistenced enabled and started"
    else
        echo "  ⚠ Could not enable nvidia-persistenced (may need manual setup)"
    fi

    # Set GPU persistence mode
    echo "Setting GPU persistence mode..."
    nvidia-smi -pm 1 > /dev/null 2>&1 && echo "  ✓ All GPUs set to persistence mode" || echo "  ⚠ Failed to set persistence mode"

    # Set GPU compute mode to EXCLUSIVE_PROCESS
    echo "Setting GPU compute mode to EXCLUSIVE_PROCESS..."
    GPU_COUNT=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)  # MIG-safe
    for (( i=0; i<$GPU_COUNT; i++ )); do
        nvidia-smi -i $i -c EXCLUSIVE_PROCESS > /dev/null 2>&1
    done
    echo "  ✓ All GPUs ($GPU_COUNT) set to EXCLUSIVE_PROCESS mode"

    # Set power limits
    echo "Setting GPU power limits..."
    echo "  GPU 0 (RTX PRO 6000): 600W"
    nvidia-smi -i 0 -pl 600 > /dev/null 2>&1 || echo "    ⚠ Failed to set power limit for GPU 0"
    echo "  GPU 1 (RTX 5090): 750W (liquid chilled)"
    nvidia-smi -i 1 -pl 750 > /dev/null 2>&1 || echo "    ⚠ Failed to set power limit for GPU 1"

    # Create systemd service for persistent power limits
    echo "Creating systemd service for persistent power limits..."
    cat > /etc/systemd/system/nvidia-power-limit.service << 'EOF'
[Unit]
Description=Set NVIDIA GPU Power Limits for AI Inference
After=nvidia-persistenced.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvidia-smi -i 0 -pl 600
ExecStart=/usr/bin/nvidia-smi -i 1 -pl 750
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable nvidia-power-limit.service > /dev/null 2>&1
    echo "  ✓ nvidia-power-limit.service created and enabled"
fi

echo ""

#
# NETWORK/IO SETTINGS
#
echo "=== 4. NETWORK/IO SETTINGS ==="

# Enable network busy polling
# Reduces network latency for remote inference APIs
echo "Configuring network busy polling..."
sysctl -w net.core.busy_poll=50 > /dev/null
sysctl -w net.core.busy_read=50 > /dev/null
echo "  ✓ net.core.busy_poll = 50"
echo "  ✓ net.core.busy_read = 50"

# Increase network buffer sizes
echo "Increasing network buffer sizes..."
sysctl -w net.core.rmem_max=134217728 > /dev/null
sysctl -w net.core.wmem_max=134217728 > /dev/null
echo "  ✓ net.core.rmem_max = 134217728 (128MB)"
echo "  ✓ net.core.wmem_max = 134217728 (128MB)"

echo ""

#
# MAKE PERSISTENT
#
echo "=== 5. MAKING CHANGES PERSISTENT ==="

# Use dedicated sysctl.d file (overwrite, not append)
SYSCTL_FILE="/etc/sysctl.d/99-ai-inference.conf"
echo "Writing to $SYSCTL_FILE (overwrites existing)..."
cat > "$SYSCTL_FILE" << EOF
# ============================================================================
# AI/LLM Inference Tuning
# Applied: $(date +"%Y-%m-%d %H:%M:%S")
# System: Threadripper PRO 9995WX + NVIDIA Blackwell
# ============================================================================

# Memory Management
vm.swappiness = 1
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
vm.compaction_proactiveness = 20
vm.nr_hugepages = 65536
kernel.numa_balancing = 0

# Scheduler
kernel.sched_autogroup_enabled = 0

# Network
net.core.busy_poll = 50
net.core.busy_read = 50
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
EOF
echo "  ✓ $SYSCTL_FILE created"

# Create systemd service for THP persistence (standardize to 'never')
echo "Creating systemd service for THP persistence..."
cat > /etc/systemd/system/disable-thp.service << 'EOF'
[Unit]
Description=Disable Transparent Huge Pages for AI Inference
After=sysinit.target local-fs.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable disable-thp.service > /dev/null 2>&1
echo "  ✓ disable-thp.service created and enabled"

echo ""

#
# SUMMARY
#
echo "============================================"
echo "  AI INFERENCE TUNING COMPLETE!"
echo "============================================"
echo ""
echo "Configured:"
echo "  ✓ Memory: Huge pages (128GB), swappiness=1, AutoNUMA disabled"
echo "  ✓ Scheduler: sched_autogroup disabled"
echo "  ✓ NVIDIA: Persistence mode, power limits, compute mode"
echo "  ✓ Network: Busy polling enabled, buffer sizes increased"
echo ""
echo "Settings made persistent in:"
echo "  - /etc/sysctl.d/99-ai-inference.conf (kernel parameters)"
echo "  - /etc/systemd/system/disable-thp.service (THP disable)"
echo "  - /etc/systemd/system/nvidia-power-limit.service (GPU power)"
echo ""
echo "IMPORTANT: Reboot required to ensure all settings take effect"
echo ""
echo "Next Steps:"
echo "  1. Reboot the system: 'reboot'"
echo "  2. After reboot, verify settings:"
echo "     /path/to/verify-ai-tuning.sh"
echo "  3. Run inference benchmark:"
echo "     llama-bench -m /models/your-model.gguf"
echo ""
echo "Documentation:"
echo "  docs/operations/linux-kernel-tuning-ai-inference.md"
echo ""
