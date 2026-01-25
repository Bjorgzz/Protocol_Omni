#!/bin/bash
# PROTOCOL PROMETHEUS: PHASE 1 (REVISED)
# Target: Kernel 6.14 (Stability) + Lazarus Flags

set -e

echo "=== PHASE 1: HOST HARDENING ==="

# 1. KERNEL PINNING (Targeting 6.14.11-5)
echo "--- Step 1: Installing Kernel 6.14.11-5 ---"
apt-get update
# Force install the specific version found in the repo
apt-get install -y proxmox-kernel-6.14.11-5-pve

echo "--- Step 2: Pinning Kernel ---"
proxmox-boot-tool kernel pin 6.14.11-5-pve
proxmox-boot-tool kernel list

# 2. LAZARUS PATCH (GRUB)
echo "--- Step 3: Applying Lazarus Flags ---"
# Backup
cp /etc/default/grub /etc/default/grub.backup.$(date +%s)

# Inject flags if not present
if ! grep -q "disable_idle_d3=1" /etc/default/grub; then
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\([^"]*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 pcie_aspm=off vfio_pci.disable_idle_d3=1"/' /etc/default/grub
    echo "Flags injected."
else
    echo "Flags already present."
fi
update-grub

# 3. OMNI-SWITCH v3.0
echo "--- Step 4: Installing Omni-Switch v3.0 ---"
cat > /usr/local/bin/omni-switch << 'SWITCH_EOF'
#!/bin/bash
# Omni-Switch v3.0 - The Lazarus Sequence
# PCI Addresses: Blackwell=f1:00, 5090=11:00

BLACKWELL_GPU="0000:f1:00.0"
BLACKWELL_AUDIO="0000:f1:00.1"
RTX5090_GPU="0000:11:00.0"
RTX5090_AUDIO="0000:11:00.1"

case "$1" in
  talos)
    echo "=== Lazarus Sequence: Binding GPUs for Talos ==="
    # 1. Unbind Audio FIRST (prevents D3 hang)
    echo "Unbinding audio devices..."
    echo "$BLACKWELL_AUDIO" > /sys/bus/pci/drivers/snd_hda_intel/unbind 2>/dev/null || true
    echo "$RTX5090_AUDIO" > /sys/bus/pci/drivers/snd_hda_intel/unbind 2>/dev/null || true
    
    # 2. Bind GPUs to vfio-pci
    echo "Binding GPUs to vfio-pci..."
    echo "vfio-pci" > /sys/bus/pci/devices/$BLACKWELL_GPU/driver_override 2>/dev/null
    echo "vfio-pci" > /sys/bus/pci/devices/$RTX5090_GPU/driver_override 2>/dev/null
    echo "$BLACKWELL_GPU" > /sys/bus/pci/drivers/vfio-pci/bind 2>/dev/null || true
    echo "$RTX5090_GPU" > /sys/bus/pci/drivers/vfio-pci/bind 2>/dev/null || true
    
    echo "Done. Run 'omni-switch status' to verify."
    ;;
  status)
    echo "=== GPU Binding Status ==="
    echo ""
    echo "Blackwell (f1:00):"
    lspci -nnks f1:00.0 | head -3
    echo ""
    echo "RTX 5090 (11:00):"
    lspci -nnks 11:00.0 | head -3
    ;;
  *)
    echo "Omni-Switch v3.0 - Lazarus Sequence"
    echo "Usage: omni-switch {talos|status}"
    ;;
esac
SWITCH_EOF

chmod +x /usr/local/bin/omni-switch
echo "SUCCESS. Host is hardened. Rebooting is required."
