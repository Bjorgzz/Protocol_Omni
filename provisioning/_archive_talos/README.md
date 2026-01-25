# Archived Talos Provisioning

These files are Talos Linux machine configuration patches from the Proxmox era.

**Superseded by:** Native Ubuntu configuration

## Files

| File | Purpose | v14.0 Equivalent |
|------|---------|------------------|
| `nvidia-patch.yaml` | NVIDIA kernel modules | Host NVIDIA driver install |
| `nvme-mount-patch.yaml` | NVMe mount | `/etc/fstab` |
| `kernel-args-patch.yaml` | Kernel parameters | `/etc/default/grub` |
| `deploy_phase2.sh` | Deployment script | `docker compose up` |

## Reason for Archive

v14.0 uses bare metal Ubuntu 24.04 instead of Talos Linux in a VM.
