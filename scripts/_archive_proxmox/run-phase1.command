#!/bin/bash
# Double-click this file to execute Phase 1 on Proxmox
cd "$(dirname "$0")/.."
echo "=== Protocol Prometheus: Phase 1 Execution ==="
echo "Connecting to Proxmox (192.168.3.10)..."
echo ""
ssh root@192.168.3.10 'bash -s' < scripts/phase1-host-hardening.sh
echo ""
echo "=== Script complete. Rebooting host in 5 seconds... ==="
sleep 5
ssh root@192.168.3.10 reboot
echo ""
echo "Host rebooting. Wait 2-3 minutes, then run verification."
echo "Press any key to close..."
read -n 1
