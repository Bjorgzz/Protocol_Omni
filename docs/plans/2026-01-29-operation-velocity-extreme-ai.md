# Operation Velocity EXTREME: AI-Priority Optimization

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Maximize AI inference throughput on Threadripper PRO 9995WX + dual GPU system (13.5-15+ tok/s target)

**Architecture:** Aggressive BIOS tuning via EFI Shell `setup_var.efi` for all 987 AmdSetupSHP settings, plus OS-level GPU/CPU optimization. Every setting prioritizes sustained bandwidth over latency spikes.

**Tech Stack:** EFI Shell, setup_var.efi, UEFI NVRAM, nvidia-smi, llama.cpp

---

## Hardware Baseline

| Component | Spec | Current | Target |
|-----------|------|---------|--------|
| CPU | 9995WX 96C/192T | 350W TDP | **1400W PPT** |
| GPU 0 | RTX PRO 6000 96GB | Stock | 600W (air) |
| GPU 1 | RTX 5090 32GB | Stock | **750W (13°C chilled)** |
| RAM | 384GB DDR5-6000 ECC | tREFI Auto | **tREFI 65535** |
| Cooling | Liquid Chiller | 13°C | Safe (>5°C) |

---

## VarStore Reference

| VarID | Name | GUID | Settings |
|-------|------|------|----------|
| 5 | Setup | `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9` | Platform (PCIe, Boot) |
| 16 | AmdSetupSHP | `3A997502-647A-4C82-998E-52EF9486A247` | Zen5 TR CBS (987 settings) |

---

## Phase 1: CPU Power Unlocking

### Task 1.1: OC Mode + Power Limits

**Files:**
- Modify: `tools/bios/extreme_settings.nsh`

**Settings:**

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| OC Mode | 0x051 | 1 | 0x00 (Normal) | Customized | **0x05** |
| PPT Control | 0x418 | 1 | 0x00 (Auto) | Manual | **0x01** |
| PPT Limit | 0x419 | 4 | 0x00 | 1400W | **0x00000578** |
| TDP Control | 0x413 | 1 | 0x00 (Auto) | Manual | **0x01** |
| TDP Limit | 0x414 | 4 | 0x00 | 350W | **0x0000015E** |
| BoostFmaxEn | 0x427 | 1 | 0x00 (Auto) | Manual | **0x01** |
| BoostFmax | 0x428 | 4 | Auto | 5700 MHz | **0x00001644** |

**EFI Shell Commands:**
```bash
rem === CPU POWER UNLOCKING ===
rem OC Mode = Customized (unlocks power controls)
setup_var.efi 0x051 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247

rem PPT = 1400W (Manual + 4-byte little-endian)
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem TDP = 350W (Manual + 4-byte)
setup_var.efi 0x413 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem BoostFmax = 5700 MHz (Manual + 4-byte, 0x1644 = 5700)
setup_var.efi 0x427 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x428 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x429 0x16 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 2: C-States & Power Management (CRITICAL FOR AI)

### Task 2.1: Disable All Sleep States

**AI Impact:** C-states add 100-500ns wake latency per memory access. For 671B model streaming weights continuously, this compounds to 5-10% throughput loss.

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| Global C-State | 0x024 | 1 | 0x01 (Enabled) | Disabled | **0x00** |
| DF C-States | 0x42D | 1 | 0x00 | Disabled | **0x00** |
| Power Supply Idle | 0x025 | 1 | Auto | Typical Current | **0x00** |
| APBDIS | 0x424 | 1 | Auto | 1 (Disable DF P-states) | **0x01** |
| DF PState Freq Optimizer | 0x42C | 1 | Auto | Disabled | **0x01** |
| Power Down Enable | 0x227 | 1 | Auto | Disabled | **0x00** |
| Determinism Control | 0x422 | 1 | Auto | Manual | **0x01** |
| Determinism Enable | 0x423 | 1 | - | Power (sustained) | **0x00** |

**EFI Shell Commands:**
```bash
rem === C-STATES & POWER MANAGEMENT (AI CRITICAL) ===
rem Global C-State = Disabled (eliminates core wake latency)
setup_var.efi 0x024 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem DF C-States = Disabled (Data Fabric must stay awake for bandwidth)
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Power Supply Idle = Typical Current (lower latency than Low Current)
setup_var.efi 0x025 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem APBDIS = 1 (completely disables DF P-state transitions)
setup_var.efi 0x424 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem DF PState Frequency Optimizer = Disabled (no dynamic frequency)
setup_var.efi 0x42C 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Power Down Enable = Disabled (memory stays active)
setup_var.efi 0x227 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Determinism = Manual + Power (prioritizes sustained throughput)
setup_var.efi 0x422 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x423 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 3: CPU Scheduling & Boost

### Task 3.1: CPPC & Core Performance

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| Core Performance Boost | 0x023 | 1 | Auto | Enabled (Auto=1) | **0x01** |
| CPPC | 0x42E | 1 | Auto | Enabled | **0x01** |
| CPPC Preferred Cores | 0x42F | 1 | Auto | Enabled | **0x01** |
| HSMP Support | 0x430 | 1 | Auto | Enabled | **0x01** |

**EFI Shell Commands:**
```bash
rem === CPU SCHEDULING & BOOST ===
rem Core Performance Boost = Auto (allows max clocks)
setup_var.efi 0x023 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem CPPC = Enabled (OS can select preferred cores)
setup_var.efi 0x42E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem CPPC Preferred Cores = Enabled (better thread placement)
setup_var.efi 0x42F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem HSMP Support = Enabled (hardware monitoring)
setup_var.efi 0x430 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 4: Prefetchers (CRITICAL FOR AI STREAMING)

### Task 4.1: Enable All Prefetchers

**AI Impact:** LLM inference streams weights sequentially. Aggressive prefetching keeps the pipeline fed, reducing memory stalls by 10-15%.

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| L1 Stream HW Prefetcher | 0x05D | 1 | 0x03 (Auto) | Enable | **0x01** |
| L1 Stride Prefetcher | 0x05E | 1 | 0x03 (Auto) | Enable | **0x01** |
| L1 Region Prefetcher | 0x05F | 1 | 0x03 (Auto) | Enable | **0x01** |
| L2 Stream HW Prefetcher | 0x060 | 1 | 0x03 (Auto) | Enable | **0x01** |
| L2 Up/Down Prefetcher | 0x061 | 1 | 0x03 (Auto) | Enable | **0x01** |
| L1 Burst Prefetch Mode | 0x062 | 1 | 0x03 (Auto) | Enable | **0x01** |

**EFI Shell Commands:**
```bash
rem === PREFETCHERS (AI STREAMING CRITICAL) ===
rem All prefetchers = Enabled (sequential weight streaming)
setup_var.efi 0x05D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x05E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x05F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x060 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x061 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x062 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 5: NUMA & Memory Fabric

### Task 5.1: Unified NUMA + Maximum Interleaving

**AI Impact:** NPS1 = single NUMA domain eliminates cross-socket memory access penalties. 2KB interleave size matches LLM weight block patterns.

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| NUMA nodes (NPS) | 0x075 | 1 | 0x07 (Auto) | NPS1 | **0x01** |
| Memory Interleaving | 0x076 | 1 | 0x07 (Auto) | Enabled | **0x01** |
| Interleave Region Size | 0x078 | 1 | 0xFF (Auto) | 2KB | **0x01** |
| DRAM Map Inversion | 0x07B | 1 | Auto | Disabled | **0x00** |
| Address Hash Bank | 0x221 | 1 | Auto | Enabled | **0x01** |
| Address Hash CS | 0x222 | 1 | Auto | Enabled | **0x01** |
| Chipselect Interleaving | 0x220 | 1 | Auto | Enabled | **0x01** |

**EFI Shell Commands:**
```bash
rem === NUMA & MEMORY FABRIC ===
rem NPS = NPS1 (single NUMA domain, no cross-socket penalty)
setup_var.efi 0x075 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Memory Interleaving = Enabled (channel interleave for bandwidth)
setup_var.efi 0x076 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Interleave Region Size = 2KB (optimal for weight streaming)
setup_var.efi 0x078 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem DRAM Map Inversion = Disabled
setup_var.efi 0x07B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Address Hashing = Enabled (better distribution)
setup_var.efi 0x221 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x222 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x220 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 6: Memory Scrubbing & ECC

### Task 6.1: Disable Background Memory Operations

**AI Impact:** Patrol scrubbing consumes memory bandwidth. During inference, disable background operations.

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| DRAM Scrub Time | 0x28C | 1 | Auto | Disabled | **0x00** |
| DRAM Redirect Scrubber | 0x28A | 1 | Auto | Disabled | **0x00** |
| Memory Clear | 0x286 | 1 | Auto | Disabled | **0x00** |
| DRAM ECC Enable | 0x283 | 1 | Auto | Enabled | **0x01** |
| DRAM UECC Retry | 0x284 | 1 | Auto | Enabled | **0x01** |

**EFI Shell Commands:**
```bash
rem === MEMORY SCRUBBING (Disable for AI) ===
rem DRAM Scrub Time = Disabled (no background scrubbing)
setup_var.efi 0x28C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Redirect Scrubber = Disabled
setup_var.efi 0x28A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Memory Clear = Disabled (faster boot)
setup_var.efi 0x286 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ECC = Keep Enabled (data integrity)
setup_var.efi 0x283 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x284 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 7: PCIe & GPU P2P (CRITICAL FOR MULTI-GPU)

### Task 7.1: Direct P2P Path

**AI Impact:** With tensor split across GPUs, weights transfer constantly. IOMMU/ACS route through CPU, adding 5-10μs latency. Direct P2P is 1-2μs.

| Setting | Offset | Width | VarID | Current | Target | Value |
|---------|--------|-------|-------|---------|--------|-------|
| IOMMU | 0x377 | 1 | 16 | 0x00 | Disabled | **0x00** |
| ACS Enable | 0x341 | 1 | 16 | 0x0F (Auto) | Disabled | **0x00** |
| PCIe ARI Enumeration | 0x343 | 1 | 16 | 0x0F (Auto) | Enabled | **0x01** |
| PCIe ARI Support | 0x344 | 1 | 16 | 0x0F (Auto) | Enabled | **0x01** |
| Above 4G Decoding | 0x102 | 1 | 5 | 0x01 | Enabled | **0x01** |
| Relaxed Ordering | 0x10B | 1 | 5 | Auto | Enabled | **0x01** |
| ATOMICOP_REQUEST | 0x35B | 1 | 16 | Auto | Enabled | **0x01** |
| ASPM Control | 0x34D | 1 | 16 | Auto | Disabled | **0x00** |

**EFI Shell Commands:**
```bash
rem === PCIe & GPU P2P (MULTI-GPU CRITICAL) ===
rem IOMMU = Disabled (direct GPU-GPU path)
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ACS = Disabled (allow P2P across PCIe switches)
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ARI = Enabled (alternative routing for large BAR)
setup_var.efi 0x343 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x344 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Above 4G Decoding = Enabled (Setup VarStore!)
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9

rem Relaxed Ordering = Enabled (better PCIe throughput)
setup_var.efi 0x10B 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9

rem AtomicOp = Enabled (GPU atomic operations)
setup_var.efi 0x35B 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ASPM = Disabled (no PCIe power management latency)
setup_var.efi 0x34D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 8: Security Features (Disable for Performance)

### Task 8.1: Disable Encryption Overhead

**AI Impact:** Memory encryption (SME/SEV/TSME) adds 3-5% overhead on every memory access.

| Setting | Offset | Width | Current | Target | Value |
|---------|--------|-------|---------|--------|-------|
| SMEE | 0x036 | 1 | Auto | Disabled | **0x00** |
| SEV Control | 0x037 | 1 | Auto | Disabled | **0x01** |
| SEV-SNP Support | 0x374 | 1 | Auto | Disabled | **0x00** |
| TSME | 0x2F9 | 1 | Auto | Disabled | **0x00** |

**EFI Shell Commands:**
```bash
rem === SECURITY (Disable for Performance) ===
rem SMEE = Disabled (no memory encryption)
setup_var.efi 0x036 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem SEV = Disabled
setup_var.efi 0x037 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem SEV-SNP = Disabled
setup_var.efi 0x374 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem TSME = Disabled
setup_var.efi 0x2F9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 9: Memory Timings (Via IFR Offsets)

### Task 9.1: Primary Timings

**Note:** All timing Ctrl offsets must be set to 0x01 (Manual) before setting values. Values are 2-byte little-endian.

| Timing | Ctrl Offset | Value Offset | Width | Target Value |
|--------|-------------|--------------|-------|--------------|
| tCL | 0x2A7 | 0x2A8 | 2 | 34 (0x0022) |
| tRCD | 0x2AA | 0x2AB | 2 | 34 (0x0022) |
| tRP | 0x2AD | 0x2AE | 2 | 34 (0x0022) |
| tRAS | 0x2B0 | 0x2B1 | 2 | 68 (0x0044) |
| tRC | 0x2B3 | 0x2B4 | 2 | 102 (0x0066) |

**EFI Shell Commands:**
```bash
rem === PRIMARY TIMINGS ===
rem tCL = 34
setup_var.efi 0x2A7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A8 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRCD = 34
setup_var.efi 0x2AA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AB 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRP = 34
setup_var.efi 0x2AD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AE 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRAS = 68
setup_var.efi 0x2B0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B1 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRC = 102
setup_var.efi 0x2B3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B4 0x66 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

### Task 9.2: Secondary Timings (Bandwidth Critical)

| Timing | Ctrl Offset | Value Offset | Width | Target Value |
|--------|-------------|--------------|-------|--------------|
| tWR | 0x2B6 | 0x2B7 | 2 | 42 (0x002A) |
| tRFC1 | 0x2B9 | 0x2BA | 2 | 420 (0x01A4) |
| tRFC2 | 0x2BC | 0x2BD | 2 | 320 (0x0140) |
| tRFCsb | 0x2BF | 0x2C0 | 2 | 240 (0x00F0) |
| tCWL | 0x2C2 | 0x2C3 | 2 | 32 (0x0020) |
| tRTP | 0x2C5 | 0x2C6 | 2 | 10 (0x000A) |

**EFI Shell Commands:**
```bash
rem === SECONDARY TIMINGS (BANDWIDTH) ===
rem tWR = 42
setup_var.efi 0x2B6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B7 0x2A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFC1 = 420
setup_var.efi 0x2B9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BA 0xA4 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFC2 = 320
setup_var.efi 0x2BC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BD 0x40 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFCsb = 240
setup_var.efi 0x2BF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C0 0xF0 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tCWL = 32
setup_var.efi 0x2C2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C3 0x20 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRTP = 10
setup_var.efi 0x2C5 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C6 0x0A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C7 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

### Task 9.3: Row/Burst Timings

| Timing | Ctrl Offset | Value Offset | Width | Target Value |
|--------|-------------|--------------|-------|--------------|
| tRRD_L | 0x2C8 | 0x2C9 | 2 | 6 (0x0006) |
| tRRD_S | 0x2CB | 0x2CC | 2 | 4 (0x0004) |
| tFAW | 0x2CE | 0x2CF | 2 | 16 (0x0010) |
| tWTR_L | 0x2D1 | 0x2D2 | 2 | 12 (0x000C) |
| tWTR_S | 0x2D4 | 0x2D5 | 2 | 4 (0x0004) |

**EFI Shell Commands:**
```bash
rem === ROW/BURST TIMINGS ===
rem tRRD_L = 6
setup_var.efi 0x2C8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C9 0x06 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CA 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRRD_S = 4
setup_var.efi 0x2CB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CC 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CD 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tFAW = 16 (CRITICAL for burst access)
setup_var.efi 0x2CE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CF 0x10 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D0 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWTR_L = 12
setup_var.efi 0x2D1 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D2 0x0C -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D3 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWTR_S = 4
setup_var.efi 0x2D4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D5 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D6 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

### Task 9.4: Turnaround Timings (AI READ CRITICAL)

**AI Impact:** LLM inference is 95% read operations. Minimizing read-to-read delay directly impacts tok/s.

| Timing | Ctrl Offset | Value Offset | Width | Target Value |
|--------|-------------|--------------|-------|--------------|
| tRDRD_ScL | 0x2D7 | 0x2D8 | 2 | 1 (0x0001) |
| tRDRD_Sc | 0x2DA | 0x2DB | 2 | 1 (0x0001) |
| tRDRD_Sd | 0x2DD | 0x2DE | 2 | 4 (0x0004) |
| tRDRD_Dd | 0x2E0 | 0x2E1 | 2 | 4 (0x0004) |
| tWRWR_ScL | 0x2E3 | 0x2E4 | 2 | 1 (0x0001) |
| tWRWR_Sc | 0x2E6 | 0x2E7 | 2 | 1 (0x0001) |
| tWRWR_Sd | 0x2E9 | 0x2EA | 2 | 4 (0x0004) |
| tWRWR_Dd | 0x2EC | 0x2ED | 2 | 4 (0x0004) |
| tWRRD | 0x2EF | 0x2F0 | 2 | 2 (0x0002) |
| tRDWR | 0x2F2 | 0x2F3 | 2 | 8 (0x0008) |

**EFI Shell Commands:**
```bash
rem === TURNAROUND TIMINGS (AI READ CRITICAL) ===
rem tRDRD_ScL = 1 (minimum same-channel read delay)
setup_var.efi 0x2D7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRDRD_Sc = 1
setup_var.efi 0x2DA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRDRD_Sd = 4
setup_var.efi 0x2DD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DE 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRDRD_Dd = 4
setup_var.efi 0x2E0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E1 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWRWR_ScL = 1
setup_var.efi 0x2E3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWRWR_Sc = 1
setup_var.efi 0x2E6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWRWR_Sd = 4
setup_var.efi 0x2E9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EA 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EB 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWRWR_Dd = 4
setup_var.efi 0x2EC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2ED 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EE 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tWRRD = 2
setup_var.efi 0x2EF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F0 0x02 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRDWR = 8
setup_var.efi 0x2F2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F3 0x08 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
```

---

## Phase 10: BIOS UI Settings (NOT in IFR)

### Task 10.1: Manual BIOS Settings

**These MUST be set via BIOS UI (KVM) - not scriptable:**

| Setting | Path | Value | AI Impact |
|---------|------|-------|-----------|
| **tREFI** | Extreme Tweaker → DRAM Timing → tREFI | **65535** | +15-20% bandwidth |
| PBO PPT | AMD Overclocking → PBO → PPT Limit | **1400W** | Unlocks power |
| PBO TDC | AMD Overclocking → PBO → TDC Limit | **1000A** | Sustained current |
| PBO EDC | AMD Overclocking → PBO → EDC Limit | **1400A** | Peak current |
| PBO Scalar | AMD Overclocking → PBO → Scalar | **10X** | Boost duration |
| Curve Optimizer | AMD Overclocking → CO | **Per-Core: -35 to -50** | Undervolt |
| FCLK | AMD CBS → DF Common → FCLK | **2100 MHz** | Max fabric speed |

---

## Phase 11: Complete EFI Shell Script

### Task 11.1: Generate extreme_settings.nsh

**File:** `tools/bios/extreme_settings.nsh`

```bash
@echo -off
rem ============================================================================
rem  OPERATION VELOCITY EXTREME - AI-Priority BIOS Optimization
rem  WRX90E-SAGE-SE BIOS 1203 | Threadripper PRO 9995WX
rem  Generated: 2026-01-29
rem  
rem  WARNING: This sets 1400W PPT, disables security features, and
rem           aggressively tunes memory. Requires 13°C liquid cooling!
rem ============================================================================

echo ============================================
echo   PHASE 1: CPU Power Unlocking
echo ============================================
rem OC Mode = Customized
setup_var.efi 0x051 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
rem PPT = 1400W
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem TDP = 350W
setup_var.efi 0x413 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem BoostFmax = 5700 MHz
setup_var.efi 0x427 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x428 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x429 0x16 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 2: C-States Disabled (AI Critical)
echo ============================================
setup_var.efi 0x024 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x025 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x424 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42C 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x227 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x422 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x423 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 3: CPU Scheduling
echo ============================================
setup_var.efi 0x023 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x430 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 4: Prefetchers Enabled (AI Critical)
echo ============================================
setup_var.efi 0x05D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x05E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x05F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x060 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x061 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x062 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 5: NUMA & Memory Fabric
echo ============================================
setup_var.efi 0x075 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x076 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x078 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x07B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x221 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x222 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x220 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 6: Memory Scrubbing Disabled
echo ============================================
setup_var.efi 0x28C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x28A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x286 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x283 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x284 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 7: PCIe P2P (Multi-GPU Critical)
echo ============================================
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x343 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x344 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
setup_var.efi 0x10B 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
setup_var.efi 0x35B 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x34D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 8: Security Disabled (Performance)
echo ============================================
setup_var.efi 0x036 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x037 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x374 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 9: Memory Timings
echo ============================================
rem PRIMARY: tCL=34, tRCD=34, tRP=34, tRAS=68, tRC=102
setup_var.efi 0x2A7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A8 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AB 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AE 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B1 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B4 0x66 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem SECONDARY: tWR=42, tRFC1=420, tRFC2=320, tRFCsb=240, tCWL=32, tRTP=10
setup_var.efi 0x2B6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B7 0x2A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BA 0xA4 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BD 0x40 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C0 0xF0 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C3 0x20 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C5 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C6 0x0A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C7 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ROW/BURST: tRRD_L=6, tRRD_S=4, tFAW=16, tWTR_L=12, tWTR_S=4
setup_var.efi 0x2C8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C9 0x06 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CA 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CC 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CD 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CF 0x10 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D0 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D1 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D2 0x0C -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D3 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D5 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D6 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem TURNAROUND: tRDRD=1/1/4/4, tWRWR=1/1/4/4, tWRRD=2, tRDWR=8
setup_var.efi 0x2D7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DE 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E1 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EA 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EB 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2ED 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EE 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F0 0x02 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F3 0x08 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   EXTREME SETTINGS COMPLETE!
echo ============================================
echo.
echo MANUAL STEPS REQUIRED (BIOS UI):
echo   1. tREFI = 65535 (Extreme Tweaker -> DRAM Timing)
echo   2. PBO PPT/TDC/EDC = 1400/1000/1400 (AMD Overclocking)
echo   3. PBO Scalar = 10X
echo   4. Curve Optimizer = Per-Core (-35 to -50)
echo   5. FCLK = 2100 MHz
echo.
echo Type 'reset' to reboot and apply settings.
```

---

## Phase 12: Verification & Benchmarking

### Task 12.1: Post-Reboot Verification

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== EXTREME SETTINGS VERIFICATION ==="

echo "--- NUMA ---"
numactl --hardware | grep -E "available|node 0"

echo "--- CPU Frequency ---"
cat /proc/cpuinfo | grep MHz | sort -rn | head -1

echo "--- GPU P2P ---"
nvidia-smi topo -m | head -5

echo "--- C-States ---"
cat /sys/devices/system/cpu/cpu0/cpuidle/state*/disable 2>/dev/null || echo "C-states controlled by BIOS"

echo "--- Memory Bandwidth ---"
if [ -f /tmp/stream/stream ]; then
    cd /tmp/stream && OMP_NUM_THREADS=192 ./stream | grep -E "Copy:|Triad:"
fi

echo "--- Inference Baseline ---"
curl -s http://localhost:8000/health && echo " [OK]" || echo " [DOWN]"
EOF
```

### Task 12.2: Performance Targets

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| tok/s Generation | 11.35 | **13.5-15** | `llama-bench` |
| tok/s Prompt Eval | 23.14 | **28-32** | `llama-bench` |
| Memory BW (Triad) | ~350 GB/s | **>420 GB/s** | STREAM |
| GPU P2P Topology | SYS (via CPU) | **PHB/PIX** | `nvidia-smi topo` |
| NUMA Nodes | Multiple | **1** | `numactl --hardware` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 EXTREME | 2026-01-29 | Complete rewrite from NUCLEAR: Added APBDIS, Determinism, BoostFmax, all memory timings with IFR offsets, security disable, Relaxed Ordering, AtomicOp |

---

*Document prepared by Verdent for Operation Velocity EXTREME. Execute via EFI Shell + BIOS UI for tREFI/PBO.*
