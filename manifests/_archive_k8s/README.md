# Archived Kubernetes Manifests

These files are from the Proxmox VE + Talos Linux + Kubernetes era (v13.x and earlier).

**Superseded by:** Docker Compose stacks in `../docker/`

## Migration Notes

| Old (K8s) | New (Docker Compose) |
|-----------|---------------------|
| `driver-validation-creator.yaml` | NVIDIA Container Toolkit on host |
| `gpu-hello-world.yaml` | `nvidia-smi` in container |
| `leviathan-deploy.yaml` | `docker/omni-stack.yaml` |
| `pvc-test.yaml` | Native NVMe mounts |
| `sysadmin-logistics.yaml` | Direct file access |

## Reason for Archive

v14.0 "SOVEREIGN GENESIS" moved from:
- Proxmox VE hypervisor → Bare metal Ubuntu 24.04
- Talos Linux → Ubuntu 24.04 Desktop
- Kubernetes → Docker Compose

This eliminates virtualization overhead and provides full 384GB RAM access.
