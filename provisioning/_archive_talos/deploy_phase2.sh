#!/bin/bash
set -e

PROXMOX_HOST="root@192.168.3.10"

echo "=========================================="
echo "PROTOCOL OMNI - PHASE 2 (ENHANCED)"
echo "=========================================="

echo ""
echo "[1/4] KERNEL CHECK"
CURRENT_KERNEL=$(ssh $PROXMOX_HOST "uname -r")
echo "Current kernel: $CURRENT_KERNEL"

if [[ "$CURRENT_KERNEL" > "6.8" ]]; then
    echo "Kernel > 6.8 detected. Pinning to 6.8..."
    ssh $PROXMOX_HOST "apt update && apt install -y proxmox-kernel-6.8"
    ssh $PROXMOX_HOST "proxmox-boot-tool kernel pin 6.8"
    echo "Kernel pinned. Verification:"
    ssh $PROXMOX_HOST "proxmox-boot-tool kernel list"
else
    echo "Kernel is already 6.8 or lower. No action needed."
fi

echo ""
echo "[2/4] LAZARUS PATCH (GRUB)"
ssh $PROXMOX_HOST 'grep -q "pcie_aspm=off" /etc/default/grub && echo "Lazarus patch already applied." || (
    cp /etc/default/grub /etc/default/grub.bak
    sed -i '\''s/GRUB_CMDLINE_LINUX_DEFAULT="\([^"]*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 pcie_aspm=off vfio_pci.disable_idle_d3=1"/'\'' /etc/default/grub
    echo "Lazarus patch applied. Running update-grub..."
    update-grub
)'
echo "GRUB config:"
ssh $PROXMOX_HOST "grep GRUB_CMDLINE_LINUX_DEFAULT /etc/default/grub"

echo ""
echo "[3/4] DEPLOYING OMNI-SWITCH v3.0"
ssh $PROXMOX_HOST 'cat > /usr/local/bin/omni-switch << '\''SCRIPT_EOF'\''
#!/bin/bash
GPU_PCI="0000:01:00"
NVME_PCI="0000:04:00.0"

unbind_device() {
    local pci=$1
    local driver_path="/sys/bus/pci/devices/$pci/driver"
    if [ -e "$driver_path" ]; then
        echo "$pci" > "$driver_path/unbind" 2>/dev/null || true
    fi
}

bind_vfio() {
    local pci=$1
    local vendor_id=$(cat /sys/bus/pci/devices/$pci/vendor 2>/dev/null | sed "s/0x//")
    local device_id=$(cat /sys/bus/pci/devices/$pci/device 2>/dev/null | sed "s/0x//")
    if [ -n "$vendor_id" ] && [ -n "$device_id" ]; then
        echo "$vendor_id $device_id" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true
        echo "$pci" > /sys/bus/pci/drivers/vfio-pci/bind 2>/dev/null || true
    fi
}

case "$1" in
    windows)
        echo "[OMNI-SWITCH] Preparing GPU and NVMe for Windows passthrough..."
        for dev in "${GPU_PCI}.0" "${GPU_PCI}.1" "$NVME_PCI"; do
            unbind_device "$dev"
            bind_vfio "$dev"
        done
        echo "[OMNI-SWITCH] Devices bound to vfio-pci."
        ;;
    release)
        echo "[OMNI-SWITCH] Releasing devices from vfio-pci..."
        for dev in "${GPU_PCI}.0" "${GPU_PCI}.1" "$NVME_PCI"; do
            echo "$dev" > /sys/bus/pci/drivers/vfio-pci/unbind 2>/dev/null || true
        done
        echo 1 > /sys/bus/pci/rescan
        echo "[OMNI-SWITCH] Devices released and PCI bus rescanned."
        ;;
    status)
        echo "[OMNI-SWITCH] Device Status:"
        for dev in "${GPU_PCI}.0" "${GPU_PCI}.1" "$NVME_PCI"; do
            driver=$(basename $(readlink /sys/bus/pci/devices/$dev/driver 2>/dev/null) 2>/dev/null || echo "unbound")
            echo "  $dev: $driver"
        done
        ;;
    *)
        echo "Usage: omni-switch {windows|release|status}"
        exit 1
        ;;
esac
SCRIPT_EOF'
ssh $PROXMOX_HOST "chmod +x /usr/local/bin/omni-switch"
echo "omni-switch deployed. Testing:"
ssh $PROXMOX_HOST "/usr/local/bin/omni-switch status"

echo ""
echo "[4/4] VERIFICATION"
echo "Kernel pin status:"
ssh $PROXMOX_HOST "proxmox-boot-tool kernel list" || echo "(proxmox-boot-tool not available)"
echo ""
echo "GRUB flags:"
ssh $PROXMOX_HOST "grep GRUB_CMDLINE_LINUX_DEFAULT /etc/default/grub"
echo ""
echo "omni-switch location:"
ssh $PROXMOX_HOST "ls -la /usr/local/bin/omni-switch"

echo ""
echo "=========================================="
echo "PHASE 2 COMPLETE"
echo "NOTE: Reboot required for kernel/GRUB changes."
echo "=========================================="
