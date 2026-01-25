# Bare Metal Deployment

> Full Ubuntu 24.04 installation for Protocol OMNI

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 32 cores | Threadripper 9995WX (96 cores) |
| **RAM** | 256GB | 384GB DDR5 ECC |
| **GPU** | 48GB VRAM | RTX 6000 96GB + RTX 5090 32GB |
| **Storage** | 2TB NVMe | 2× 4TB Gen5 NVMe |
| **Network** | 1Gbps | 10Gbps |

## 1. BIOS Configuration

### Critical Settings

| Setting | Value | Location |
|---------|-------|----------|
| NPS | 4 | AMD CBS → DF |
| PCIe Link Speed | Gen5 | AMD CBS → NBIO |
| RAM Speed | 6400 MT/s | AMD CBS → UMC |
| IOMMU | Enabled | AMD CBS → NBIO |

### PCIe Fix (Critical)

If GPUs show Gen1 (2.5GT/s) instead of Gen5 (32GT/s):

1. Access BIOS via BMC (https://192.168.3.202)
2. Navigate to AMD CBS → NBIO → PCIe
3. Set `CbsCmnEarlyLinkSpeedSHP` → GEN5
4. Cold reboot (power cycle)

```bash
# Verify
nvidia-smi --query-gpu=name,pcie.link.gen.current,pcie.link.width.current --format=csv
# Expected: 5, 16
```

## 2. Ubuntu Installation

### Partition Layout

```
NVMe 0 (Crucial 4TB) - Ubuntu 24.04
├── /boot/efi     512MB   EFI System Partition
├── /             500GB   ext4 root
├── /home         500GB   ext4 user data
└── /nvme         ~3TB    XFS for models/data
```

### Post-Install

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y build-essential git curl wget htop nvtop

# Set hostname
sudo hostnamectl set-hostname omni-prime
```

## 3. NVIDIA Driver Installation

```bash
# Add NVIDIA repository
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# Install driver 580.x
sudo apt install -y nvidia-driver-580

# Reboot
sudo reboot

# Verify
nvidia-smi
```

## 4. Docker Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:13.0.1-base-ubi9 nvidia-smi
```

## 5. Storage Setup

```bash
# Create directories
sudo mkdir -p /nvme/{models,prompts,mem0,letta,memgraph,qdrant,prometheus,grafana,phoenix}
sudo chown -R $USER:$USER /nvme

# Clone repository (replace YOUR-ORG with actual organization)
cd ~
git clone https://github.com/YOUR-ORG/Protocol_Omni.git
```

## 6. Model Download

```bash
# Install HuggingFace CLI
pip install huggingface-cli

# Download DeepSeek-V3.2 (DQ3_K_M - ~281GB)
huggingface-cli download unsloth/DeepSeek-V3.2-GGUF \
  --include "*DQ3_K_M*" \
  --local-dir /nvme/models/deepseek-v3.2-dq3

# Download GLM-4.7 (optional)
huggingface-cli download THUDM/glm-4-9b-chat \
  --local-dir /nvme/models/glm-4.7
```

## 7. Deploy Stack

```bash
cd ~/Protocol_Omni/docker

# Start full stack
docker compose -f omni-stack.yaml --profile full up -d

# Monitor startup (3-5 min for model load)
docker compose -f omni-stack.yaml logs -f deepseek-v32
```

## 8. Verify Deployment

```bash
# Check all services
docker compose -f omni-stack.yaml ps

# Test inference
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# Test chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3.2", "messages": [{"role": "user", "content": "Hello"}]}'

# Check GPU utilization
nvidia-smi

# Access Grafana
open http://192.168.3.10:3000
```

## Kernel Parameters

Add to `/etc/default/grub`:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash pcie_aspm=off iommu=pt amd_iommu=on vfio_pci.disable_idle_d3=1 initcall_blacklist=sysfb_init"
```

| Parameter | Purpose |
|-----------|---------|
| `pcie_aspm=off` | Disable PCIe power saving (stability) |
| `iommu=pt` | Passthrough mode for GPU |
| `amd_iommu=on` | Enable AMD IOMMU |
| `vfio_pci.disable_idle_d3=1` | **CRITICAL**: Prevents RTX 5090 sleep state → FLR Reset Bug |
| `initcall_blacklist=sysfb_init` | **CRITICAL**: Prevents boot splash VRAM lock |

Then:

```bash
sudo update-grub
sudo reboot
```

Verify:

```bash
cat /proc/cmdline | grep -E "vfio_pci.disable_idle_d3|initcall_blacklist"
```

## Firewall

```bash
# Allow required ports
sudo ufw allow ssh
sudo ufw allow 8000:8100/tcp  # Inference APIs
sudo ufw allow 3000/tcp       # Grafana
sudo ufw allow 9090/tcp       # Prometheus
sudo ufw enable
```

## Next Steps

- [k3s Production](k3s-production.md) - Production deployment with Zone A/B
- [Monitoring](../operations/monitoring.md) - Set up observability
- [Troubleshooting](../operations/troubleshooting.md) - Common issues
