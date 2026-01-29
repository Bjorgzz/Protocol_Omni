# BIOS Baseline Export - 2026-01-29

**System:** Threadripper PRO 9995WX + RTX PRO 6000 (96GB) + RTX 5090 (32GB)
**Export Time:** Thu Jan 29 17:26:49 UTC 2026 (post-reboot with "previous" settings)

## EFI Variable Export (via efivars)

### CPU Power (AmdSetupSHP VarStore)
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| OC Mode | 0x51 | 0x00 | Normal/Auto |
| PPT Control | 0x418 | 0x00 | Auto |
| PPT Limit | 0x419-41C | 0x00000000 | Auto |
| TDP Control | 0x413 | 0x00 | Auto |
| TDP Limit | 0x414-417 | 0x00000000 | Auto |

### C-States
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| Global C-State | 0x24 | **0x00** | **DISABLED** (good!) |
| DF C-States | 0x42D | 0x0F | Auto |
| APBDIS | 0x424 | 0x0F | Auto |

### GPU P2P
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| IOMMU | 0x377 | 0x0F | Auto |
| ACS | 0x341 | 0x0F | Auto |
| GPU Topology | - | NODE | Not optimal (want PHB/PIX) |

### Memory/Fabric
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| NPS Mode | 0x75 | 0x07 | Auto (showing as NPS1) |
| Mem Interleave | 0x76 | 0x07 | Auto |
| Mem Intlv Size | 0x78 | 0xFF | Auto |

### Prefetchers
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| L1 Stream | 0x5D | 0x03 | Auto |
| L1 Stride | 0x5E | 0x03 | Auto |
| L1 Region | 0x5F | 0x03 | Auto |
| L2 Stream | 0x60 | 0x03 | Auto |
| L2 UpDown | 0x61 | 0x03 | Auto |
| L1 Burst | 0x62 | 0x03 | Auto |

### Platform (Setup VarStore)
| Setting | Offset | Value | Interpretation |
|---------|--------|-------|----------------|
| Above 4G Decode | 0x102 | 0x01 | Enabled (good!) |

---

## System State

```
NUMA: 1 node (NPS1 effective via Auto)
Memory: 377Gi total, 369Gi available
Swap: 208Gi (8G + 200G NVMe)
GPUs: Both detected, PRO 6000 + 5090
```

---

## Benchmark Results

**llama.cpp Build:** b7869 (ghcr.io/ggml-org/llama.cpp:server-cuda)
**Model:** DeepSeek-R1-0528 Q4_K_M (377GB split GGUF)
**Config:** `-ngl 10 -sm none -c 4096 --cache-type-k q4_1 --flash-attn on`

| Run | Tokens | Time | Throughput |
|-----|--------|------|------------|
| 1 (cold) | 300 | 54.5s | 5.50 tok/s |
| 2 (warm) | 300 | 29.2s | 10.27 tok/s |
| 3 (warm) | 300 | 27.4s | 10.93 tok/s |

**Baseline: ~10.6 tok/s** (warm average)

---

## Key Findings

1. **Global C-State already DISABLED** (0x00) - one optimization already in place
2. **DF C-States, APBDIS on Auto** - needs explicit disable for AI bandwidth
3. **Power limits on Auto** - PBO not enabled (PPT = 0)
4. **GPU P2P showing NODE** - IOMMU/ACS on Auto blocking direct path
5. **Prefetchers on Auto** - should explicitly enable all 6
6. **NPS on Auto** - showing as NPS1 but should explicitly set
