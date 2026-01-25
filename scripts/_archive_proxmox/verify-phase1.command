#!/bin/bash
# Double-click this file to verify Phase 1
echo "=== Protocol Prometheus: Phase 1 Verification ==="
echo "Connecting to Proxmox (192.168.3.10)..."
echo ""
ssh root@192.168.3.10 '
echo "Kernel: $(uname -r)"
echo ""
echo "Cmdline flags:"
cat /proc/cmdline | tr " " "\n" | grep -E "pcie_aspm|disable_idle_d3|iommu"
echo ""
echo "=== omni-switch status ==="
/usr/local/bin/omni-switch status
'
echo ""
echo "=== Verification complete ==="
echo "Press any key to close..."
read -n 1
