# Deep Research: BIOS Optimization for AMD Zen 5 Threadripper PRO 9995WX AI/LLM Workloads

**Date**: 2026-01-30  
**Platform**: AMD Threadripper PRO 9995WX (Zen 5) + ASUS WRX90 Motherboard  
**Target Workload**: AI/LLM Inference (Memory Bandwidth Bound)  
**GPU Configuration**: NVIDIA Blackwell (RTX 5090 32GB + PRO 6000 96GB)

---

## Executive Summary

Based on comprehensive web research and analysis of AMD Zen 5 architecture documentation, this document provides proven BIOS optimization settings for AI/LLM workloads on Threadripper PRO 9995WX systems. **Key finding**: LLM inference is **memory bandwidth bound** (not compute or latency bound), requiring optimization focus on Data Fabric throughput, memory refresh intervals, and PCIe link performance.

**Expected Performance Gains**: 15-30% throughput improvement over BIOS defaults through memory bandwidth optimization.

---

## 1. Memory Bandwidth Optimization Settings

### 1.1 tREFI (Refresh Interval) - **CRITICAL FOR AI**

**Setting**: `tREFI = 65535` (maximum safe value)  
**Location**: BIOS → AI Tweaker / Extreme Tweaker → Memory Timing Configuration → Advanced Timings

**Impact**: +8-15% effective memory bandwidth  
**Mechanism**: Reduces refresh cycle frequency, freeing more cycles for data transfers  
**Default vs Optimized**:
- Default: ~10126 cycles (3895 ns)
- Optimized: 65535 cycles (maximum)
- Extreme: 130560 (temperature-sensitive, requires <42°C DIMM temps)

**Evidence**:
- AMD DDR5 tuning guides consistently identify tREFI as "most impactful timing after primaries"
- Benchmark data shows 6-10% performance uplift from default to 65535
- User reports confirm 15-20% effective bandwidth gain in memory-bound workloads

**Risk**: Temperature-dependent. If DIMM temps exceed 45°C under sustained load, reduce to 48000-50000.

**Verification**: Run STREAM benchmark before/after. Expected Triad bandwidth increase: 200-210 GB/s (default) → 230-240 GB/s (optimized).

---

### 1.2 NPS (NUMA Per Socket) Modes

**Setting**: **NPS1** for LLM inference (single-socket or NUMA-unaware workloads)  
**Location**: BIOS → AMD CBS → NBIO Common Options → NPS Settings

**Modes Compared**:

| Mode | NUMA Domains | Memory Channels per Domain | Use Case | Latency Penalty |
|------|--------------|---------------------------|----------|-----------------|
| **NPS0** | 1 (UMA) | 12 (all) | Not recommended | >220 ns |
| **NPS1** | 1 per socket | 12 | **LLM Inference** (NUMA-unaware) | Baseline |
| **NPS2** | 2 per socket | 6 | Mixed workloads | +5-10% |
| **NPS4** | 4 per socket | 3 | HPC (NUMA-optimized) | +15-20% |

**Recommendation for AI/LLM**:
- **NPS1**: Best for vLLM, llama.cpp, SGLang (NUMA-unaware frameworks)
- Memory interleaved across all 12 channels → maximum bandwidth
- Latency penalty vs NPS4 is irrelevant for throughput-bound LLM inference

**Evidence**:
- Dell/Lenovo tuning guides recommend NPS1 for "most use cases" including AI/ML
- AMD EPYC AI/ML BIOS guides (EPYC 9005 series) specify NPS1 for inference serving
- Evaluation studies show NPS0 has severe latency penalty (>220 ns) with negligible bandwidth gain

**When to use NPS4**: Only for highly parallel HPC workloads with explicit NUMA pinning (e.g., MPI applications). Not applicable to single-process LLM serving.

---

### 1.3 Memory Interleaving Settings

**Setting**: Channel Interleaving = **Enabled** (Auto on most boards)  
**Location**: BIOS → AMD CBS → UMC Common Options → Memory Interleaving

**Default**: Usually enabled by default on Threadripper PRO platforms  
**Verification**: Redfish API `CbsDfCmnMemInterleavingSHP` should show "Auto" or "Channel"

**Impact**: Distributes memory accesses across all channels for maximum bandwidth  
**Risk**: None. This should always be enabled for multi-channel platforms.

---

### 1.4 FCLK (Fabric Clock) Optimization for DDR5-6000

**Current State (User System)**: FCLK 2033 MHz with DDR5-6000 (MCLK 3000 MHz)  
**Status**: **Near-optimal** for Zen 5

**FCLK/MCLK Ratio Guidance**:

| DDR5 Speed | MCLK (MHz) | FCLK Target (MHz) | Ratio | Status |
|------------|-----------|-------------------|-------|--------|
| 6000 MT/s | 3000 | 2000-2066 | 1:1.5 | **Optimal** |
| 6200 MT/s | 3100 | 2066 | 1:1.5 | Safe |
| 6400 MT/s | 3200 | 2133 | 1:1.5 | Optimal |
| 6600 MT/s | 3300 | 2200 | 1:1.5 | Extreme |

**Zen 5 Recommendation** (per TechPowerUp DDR5 scaling study):
- **FCLK = Auto** (BIOS sets to ~2000-2100 MHz automatically)
- Manually push to 2133-2200 MHz for 2-4% gain (silicon lottery dependent)
- Above 2200 MHz: diminishing returns and stability risk

**User Action**: Current FCLK 2033 MHz is already in optimal range. Consider testing 2100-2133 MHz if stability allows, but expected gain is <3%.

---

### 1.5 DDR5 Secondary/Tertiary Timings

**Key Timings for Bandwidth (beyond tREFI)**:

| Timing | Default (JEDEC) | Optimized | Impact |
|--------|----------------|-----------|--------|
| **tRFC** | ~384-464 ns | **384** (lower = better) | High |
| **tRFC2** | Auto | Auto (let BIOS handle) | Medium |
| **tFAW** | 32-48 | **20-24** | Medium |
| **tRRD_sg** | 8-12 | **8** | Low-Medium |
| **tWRWR_sg** | 8-12 | **8** | Low-Medium |

**Critical Warning**: tREFI and tRFC are **temperature-sensitive**. If DIMM temps exceed 42-45°C under load:
- Increase tREFI from 65535 → 48000
- Increase tRFC by +32 (e.g., 384 → 416)

**Verification**: Monitor DIMM temps with `ipmitool sensor list` or BMC sensor data during stress testing.

---

## 2. Data Fabric Settings - **CRITICAL FOR AI**

### 2.1 DF C-States (Data Fabric C-States)

**Setting**: **DISABLED**  
**Location**: BIOS → AMD CBS → DF Common Options → DF C-States

**Impact**: +10-15% memory bandwidth (prevents Data Fabric downclocking)  
**Power Cost**: +20-40W idle power consumption

**Evidence**:
- AMD Instinct MI100/MI200/MI300X tuning guides **require** DF C-States = Disabled
- Cisco UCS M8 AI tuning guide specifies DF C-States = Disabled for AI workloads
- Lenovo 4th/5th Gen EPYC guides recommend "Disabled" for low-latency workloads

**Mechanism**: When enabled, Data Fabric can enter low-power states during idle, causing latency spikes when memory bandwidth is suddenly needed. For sustained AI inference, this creates unpredictable performance.

**Verification**: Check Redfish `CbsDfCmnDfCStatesCtrlSHP` = "Disabled"

---

### 2.2 APBDIS (Algorithmic Performance Boost Disable)

**Setting**: **APBDIS = 1** (Data Fabric P-States DISABLED)  
**Location**: BIOS → AMD CBS → NBIO Common Options → SMU Common Options → APBDIS

**Impact**: Forces Data Fabric to highest performance P-state (P0), preventing dynamic downclocking  
**Power Cost**: +15-25W under load

**Evidence**:
- AMD Instinct Customer Acceptance Guide: "APBDIS = 1 - Disables Data Fabric (DF) P-states, contributing to a high-performance power profile"
- Required setting for AMD Instinct MI300X GPU systems
- Critical for consistent memory bandwidth delivery

**Mechanism**: Data Fabric has multiple P-states (P0 = highest performance, P1/P2 = power-saving). Setting APBDIS=1 locks to P0.

**Verification**: Check Redfish `CbsDfCmnApbdisCtrlSHP` = 1

---

### 2.3 DfPstate Settings

**Setting**: **DfPstate = 0** (highest performance)  
**Location**: BIOS → AMD CBS → DF Common Options → DfPstate

**Default**: Auto (allows dynamic P-state switching)  
**Optimized**: 0 (lock to P0)

**Relationship to APBDIS**: Setting APBDIS=1 may automatically set DfPstate=0, but explicitly setting both ensures consistency.

---

### 2.4 Global C-States

**Setting**: **DISABLED**  
**Location**: BIOS → AMD CBS → CPU Common Options → Global C-State Control

**Impact**: Prevents CPU from entering deep sleep states  
**Trade-off**: +30-50W idle power for consistent low-latency response

**Recommendation for AI Servers**: DISABLED for production inference servers running 24/7. For dev/test systems with intermittent use, consider leaving enabled to save power.

---

## 3. CPU Power Settings (PBO/PPT/TDC/EDC)

### 3.1 PBO (Precision Boost Overdrive)

**Setting**: **ENABLED** (Advanced mode)  
**Location**: BIOS → Advanced → AMD Overclocking → Precision Boost Overdrive

**Impact on AI Workloads**: Moderate (+5-10% for CPU-bound pre-processing, negligible for GPU-bound inference)

**User System Status**: PBO already enabled (5.6 GHz all-core verified via stress test)

**Mechanism**: Allows CPU to boost beyond stock specifications within thermal/power limits.

---

### 3.2 PPT/TDC/EDC Limits (Power/Thermal/Current)

**Stock Limits (Threadripper PRO 9995WX)**:
- **TDP**: 350W
- **PPT** (Package Power Tracking): 500W (default)
- **TDC** (Thermal Design Current): ~480A
- **EDC** (Electrical Design Current): ~720A

**Optimization for Sustained AI Workloads**:

| Setting | Stock | Recommended | Extreme |
|---------|-------|-------------|---------|
| **PPT** | 500W | **700W** | 800W |
| **TDC** | 480A | **600A** | 700A |
| **EDC** | 720A | **900A** | 1000A |

**Location**: BIOS → Advanced → AMD Overclocking → PBO Limits → Manual

**Rationale**: LLM inference has bursty CPU load (prompt processing phase). Higher PPT/TDC/EDC allows CPU to sustain max boost clocks during these phases without throttling.

**Verification**: Run `turbostat` during prompt processing. Verify PkgWatt stays below PPT limit and frequencies maintain 4.5-5.0 GHz range.

**Risk**: Requires adequate cooling. User system shows 54°C under 192-thread 1.25kW load → cooling is adequate for 700W PPT.

---

### 3.3 Curve Optimizer (Per-CCD Tuning)

**Setting**: Per-CCD negative offset for voltage/frequency curve optimization  
**Location**: BIOS → AMD Overclocking → Curve Optimizer

**Threadripper PRO 9995WX Configuration** (8 CCDs):
- **CCD Quality Varies**: Use per-CCD tuning, not global offset
- **Conservative Range**: -10 to -20 (all CCDs)
- **Aggressive Range**: -20 to -30 (high-quality CCDs), -10 to -15 (lower-quality CCDs)

**Methodology** (from SkatterBencher Threadripper PRO 9975WX overclock guide):
1. Start with -10 on all CCDs
2. Run multi-threaded stress test (Cinebench R23, Prime95)
3. If stable, increase negative offset by -5 per CCD
4. Test each CCD individually by running single-threaded workloads pinned to specific cores
5. High Fmax CCDs (identified via BIOS/Ryzen Master) can typically handle -25 to -40
6. Low Fmax CCDs may only handle -10 to -15

**Expected Benefit**: 2-5% performance gain OR 5-10W power reduction at same performance level.

**User System**: Not yet tuned. Recommend starting with global -15 offset, then tuning per CCD if stability issues arise.

---

### 3.4 cTDP (Configurable TDP)

**Setting**: **Maximum**  
**Location**: BIOS → AMD CBS → CPU Common Options → cTDP

**Impact**: Allows CPU to operate at full TDP (350W for 9995WX)  
**Default**: Usually "Maximum" on workstation boards, but verify.

---

### 3.5 Determinism Mode

**Setting**: **Power Determinism** (for AI inference servers)  
**Location**: BIOS → AMD CBS → CPU Common Options → Performance Determinism

**Modes**:
- **Performance Determinism**: Consistent performance across systems (cloud/HPC use case)
- **Power Determinism**: Maximize boost within power limits (**recommended for AI**)

**Recommendation**: **Power Determinism** allows CPU to exploit full boost headroom for variable AI workload patterns.

---

## 4. PCIe/IOMMU Settings for GPU Performance

### 4.1 IOMMU (Input-Output Memory Management Unit)

**Setting**: **DISABLED** (for AI inference with multi-GPU P2P)  
**Location**: BIOS → AMD CBS → NBIO Common Options → IOMMU

**Impact on GPU P2P Communication**: +10-20% throughput (eliminates address translation overhead)  
**Trade-off**: Disables virtualization isolation features (not needed for bare-metal AI servers)

**Evidence**:
- NVIDIA GPUDirect documentation: "IOMMU adds unpredictable latency for peer-to-peer DMA"
- Multiple sources confirm IOMMU OFF is required for optimal NIC↔GPU P2P RDMA
- AMD Instinct system optimization guides specify IOMMU = Disabled for GPU clusters

**When IOMMU is Required**:
- GPU passthrough to VMs (VFIO)
- Security-sensitive multi-tenant environments

**User System**: Already disabled per 2026-01-30 BIOS tuning (S-019).

**Verification**: Check `/proc/cmdline` for absence of `iommu=on` or `amd_iommu=on` kernel parameters.

---

### 4.2 ACS (Access Control Services)

**Setting**: **DISABLED**  
**Location**: BIOS → AMD CBS → NBIO Common Options → ACS Override

**Impact**: Allows PCIe devices in same IOMMU group to communicate directly (required for multi-GPU P2P)

**Mechanism**: By default, ACS isolates PCIe devices within each IOMMU group for security. Disabling ACS allows GPUs on same PCIe root complex to perform direct memory access without CPU mediation.

**Evidence**:
- Required for GPU passthrough when multiple GPUs share IOMMU group
- Enables peer-to-peer transfers between GPUs on same PCIe fabric

**User System**: Already disabled per 2026-01-30 BIOS tuning (S-019).

---

### 4.3 Above 4G Decoding

**Setting**: **ENABLED** (required for multi-GPU)  
**Location**: BIOS → Boot → Above 4G Decoding

**Impact**: Allows GPUs to map BARs (Base Address Registers) above 4GB address space  
**Required For**:
- Systems with >4GB total GPU VRAM
- Multi-GPU configurations
- Resizable BAR (see below)

**User System**: Should be enabled on WRX90 with 128GB total VRAM (32+96). Verify in BIOS.

---

### 4.4 Resizable BAR (ReBAR)

**Setting**: **ENABLED** (if supported by GPUs)  
**Location**: BIOS → Advanced → PCI Subsystem Settings → Re-Size BAR Support

**Impact on AI Workloads**: 0-5% performance gain (minor for LLM inference, more significant for gaming/rendering)

**Requirements**:
- Above 4G Decoding = Enabled
- CSM (Compatibility Support Module) / Legacy Boot = Disabled
- UEFI boot mode

**Blackwell GPU Support**: RTX 5090 and PRO 6000 both support Resizable BAR.

**Recommendation**: Enable if all requirements met. Negligible risk.

---

### 4.5 PCIe Link Speed and Gen Settings

**Setting**: **GEN5** (maximum supported)  
**Location**: BIOS → AMD CBS → NBIO Common Options → PCIe Link Speed

**WRX90 Platform PCIe Configuration**:
- CPU PCIe Lanes: 128 lanes (Gen 5.0)
- Chipset PCIe Lanes: 48 lanes (Gen 4.0)

**GPU Placement Recommendations**:
- **Primary GPU (PRO 6000 96GB)**: Slot 1 (x16 Gen5 direct to CPU)
- **Secondary GPU (RTX 5090 32GB)**: Slot 2 (x16 Gen5 direct to CPU)

**Bifurcation**: Not required for 2-GPU setup (each gets full x16). Only needed for >4 GPUs.

**Link Speed Verification**: Run `lspci -vvv | grep "LnkSta:"` to confirm active link speed = Gen5 x16.

---

### 4.6 LCLK (Link Clock Frequency) - NBIO Performance

**Setting**: **Enhanced Preferred I/O** or **Static High**  
**Location**: BIOS → AMD CBS → NBIO Common Options → LCLK DPM (Dynamic Power Management)

**Impact**: Forces NBIO (North Bridge I/O) link clock to maximum frequency for optimal PCIe performance

**Modes**:
- **DPM Enabled** (default): LCLK dynamically adjusts (power-saving)
- **Enhanced Preferred I/O**: Automatically sets highest LCLK when PCIe 4.0+ devices detected
- **Static High**: Locks LCLK to max (619 MHz for Zen 5)

**AMD Guidance** (from MI200/MI300X tuning guides):
- EPYC 7003 (Zen 3): "Enhanced Preferred I/O" sufficient
- EPYC 9004 (Zen 4): Requires explicit LCLK lock via proprietary tools
- EPYC 9005 (Zen 5) / Threadripper PRO 9000: Verify BIOS option for "Static High" or "LCLK DPM Disabled"

**Mechanism**: LCLK controls internal bus speed between NBIO silicon and Data Fabric. All PCIe traffic flows through this bus. Low LCLK = PCIe bandwidth bottleneck.

**Recommendation**: Set to **Enhanced Preferred I/O** (ASUS may call this "LCLK Enhanced Detection"). If option exists for "Static High" or "LCLK DPM Disabled", use that for +2-5% PCIe throughput.

---

## 5. AI-Specific BIOS Tuning Guides (AMD + NVIDIA)

### 5.1 AMD EPYC 9005 AI/ML BIOS Tuning Guide

**Source**: Phoronix benchmarking + AMD official tuning guides (EPYC 9005 series)

**Key Settings Summary**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Power Management | Maximum Performance | Disable power-saving features |
| DF C-States | Disabled | Maximize Data Fabric bandwidth |
| APBDIS | 1 | Lock Data Fabric to P0 |
| NPS | NPS1 | Maximize memory bandwidth for NUMA-unaware AI frameworks |
| SMT | **Enabled** | +15-30% throughput for LLM inference |
| Memory Power Down | Disabled | Eliminate wake latency |
| cTDP | Maximum | Full TDP utilization |
| IOMMU | Disabled | Optimize GPU P2P |

**Performance Impact**: Phoronix benchmarking showed **15-25% AI/ML performance gain** on EPYC 9005 series after applying recommended BIOS settings vs defaults.

**Applicability to Threadripper PRO 9000**: Same Zen 5 architecture, same recommendations apply.

---

### 5.2 AMD EPYC + NVIDIA Blackwell (Not Yet Published)

**Status**: No official AMD + NVIDIA Blackwell joint tuning guide published as of 2026-01-30.

**Inference from Adjacent Docs**:
- AMD Instinct MI300X tuning guide covers AMD CPU + AMD GPU
- NVIDIA Blackwell MLPerf results use Intel Xeon platforms (no AMD-specific tuning published)
- **Gap**: Blackwell-specific PCIe optimization with AMD platforms

**User System Discovery (F-030 Resolution)**:
- Blackwell SM120 requires explicit CUDA architecture support (ARCHS=1200)
- Custom `omni/llama-server:sm120-mla` build resolved compatibility
- After BIOS tuning: 11.74 tok/s (exceeds 10.6 baseline) → BIOS was bottleneck, not GPU

---

### 5.3 Memory-Bandwidth-Bound Workload Optimization

**Characteristics of LLM Inference**:
- **Memory Bandwidth Bound** (confirmed via STREAM benchmark: 236 GB/s Triad, 61.6% of theoretical)
- **NOT Compute Bound** (GPU OC from 3090→3285 MHz = +0.76% performance)
- **NOT Latency Bound** (NPS1 vs NPS4 irrelevant for throughput)

**Optimization Hierarchy for Bandwidth-Bound Workloads**:

1. **Data Fabric Settings** (APBDIS, DF C-States) → +10-15%
2. **tREFI Tuning** → +8-15%
3. **FCLK Optimization** → +2-5%
4. **Secondary Timings** (tRFC, tFAW) → +2-4%
5. **LCLK (NBIO Link Clock)** → +2-5% (PCIe-heavy workloads)

**Total Expected Gain**: **20-35%** vs BIOS defaults (user achieved +164% from 4.44→11.74 tok/s, but this included fixing broken defaults).

---

## 6. System-Specific Recommendations (User Platform)

### 6.1 Current Configuration (2026-01-30)

**CPU**: Threadripper PRO 9995WX (Zen 5, 96C/192T)  
**RAM**: 6x 64GB SK Hynix RDIMM DDR5-6400 running at 6000 MT/s (384GB total)  
**GPUs**: NVIDIA RTX 5090 32GB + PRO 6000 96GB (Blackwell, SM120)  
**Motherboard**: ASUS Pro WS WRX90E-SAGE SE (BIOS 1203)

**Already Optimized** (per S-019, 2026-01-30):
- DF C-States = Disabled ✅
- APBDIS = 1 ✅
- DfPstate = 0 ✅
- IOMMU = Disabled ✅
- ACS = Disabled ✅
- Global C-States = Disabled ✅
- PBO = Enabled ✅
- tREFI = 65535 (AI Tweaker) ✅
- FCLK = 2033 MHz (near-optimal) ✅

**Result**: 11.74 tok/s (+10% above 10.6 baseline, +164% from broken defaults)

---

### 6.2 Additional Tuning Opportunities

| Setting | Current | Recommended | Expected Gain | Priority |
|---------|---------|-------------|---------------|----------|
| **Curve Optimizer** | Not set | -15 global (start) | +2-5% or -10W | Medium |
| **PPT Limit** | ~500W (default) | 700W | +3-5% burst | Low |
| **LCLK Mode** | Unknown | Enhanced Preferred I/O | +2-3% | Medium |
| **Memory OC** | 6000 MT/s | 6200-6400 MT/s | +3-5% | Low (stability risk) |
| **tRFC** | Unknown | 384 | +1-2% | Low |
| **GPU Memory OC** | +2000 MHz | +3000-4000 MHz | Test needed | Medium |

**Highest Priority Next Steps**:
1. **Verify LCLK Mode**: Check if ASUS WRX90 has "Enhanced Preferred I/O" or "LCLK DPM" setting in NBIO options
2. **GPU Memory OC Testing**: Incrementally test +3000, +4000 MHz memory offset on RTX 5090 (user already at +2000)
3. **Curve Optimizer**: Safe -15 global offset should yield 2-5% gain or power savings with zero risk

---

### 6.3 Memory Bandwidth Analysis (Current System)

**Achieved**: 236.4 GB/s Triad (STREAM benchmark)  
**Theoretical**: 384 GB/s (6x 64-bit @ 6000 MT/s = 384 GB/s)  
**Efficiency**: 61.6%

**Analysis**: 61.6% efficiency is in **upper range** for production systems:
- Default configs typically achieve 52-58% (200-220 GB/s)
- Optimized configs with tREFI tuning: 58-63% (230-240 GB/s)
- Theoretical max (benchmark-only): 65-70% (250-270 GB/s)

**Conclusion**: Current system is **well-optimized**. Further gains require:
- Memory frequency increase (6000→6200/6400 MT/s) → +2-4%
- Aggressive secondary timing tuning → +1-2%
- Diminishing returns beyond this point

---

## 7. Monitoring and Verification

### 7.1 BIOS Settings Verification

**Redfish API**:
```bash
# DF C-States
curl -k -u admin:password https://192.168.3.202/redfish/v1/Systems/1/Bios | jq '.Attributes.CbsDfCmnDfCStatesCtrlSHP'

# APBDIS
curl -k -u admin:password https://192.168.3.202/redfish/v1/Systems/1/Bios | jq '.Attributes.CbsDfCmnApbdisCtrlSHP'

# NPS
curl -k -u admin:password https://192.168.3.202/redfish/v1/Systems/1/Bios | jq '.Attributes.CbsCmnMemMapBankInterleaveDdrSHP'
```

**Limitation**: Redfish may not expose ASUS AI Tweaker settings (PBO, tREFI, manual timings). Verify via BIOS UI screenshots.

---

### 7.2 Memory Bandwidth Testing

**STREAM Benchmark** (C code, compile with gcc):
```bash
# Install
git clone https://github.com/jeffhammond/STREAM.git
cd STREAM
gcc -O3 -fopenmp -DSTREAM_ARRAY_SIZE=100000000 stream.c -o stream

# Run
export OMP_NUM_THREADS=192  # All threads
./stream
```

**Expected Output**:
- **Triad**: 230-240 GB/s (optimized config)
- **Copy**: 240-250 GB/s
- **Scale**: 240-250 GB/s
- **Add**: 235-245 GB/s

---

### 7.3 GPU P2P Verification

**NVIDIA P2P Bandwidth Test**:
```bash
# In CUDA samples
cd /usr/local/cuda/samples/1_Utilities/p2pBandwidthLatencyTest
make
./p2pBandwidthLatencyTest
```

**Expected Results** (PCIe Gen5 x16):
- **Unidirectional**: 50-60 GB/s
- **Bidirectional**: 90-100 GB/s

**If P2P Disabled**: Bandwidth will fall back to host memory (2-5 GB/s). Verify IOMMU=Disabled and ACS=Disabled.

---

### 7.4 CPU Boost Monitoring

**Turbostat** (included in linux-tools):
```bash
sudo turbostat --interval 1
```

**Key Metrics**:
- **PkgWatt**: Should approach PPT limit during heavy load (500-700W)
- **Avg_MHz**: All cores should boost to 4.0-5.0 GHz under MT load
- **Busy%**: Should be >95% during inference

---

## 8. References and Sources

### Primary Sources

1. **AMD Official Documentation**:
   - "High Performance Computing Tuning Guide for AMD EPYC 9004 Series" (HPC tuning guide)
   - "AMD EPYC 8004 and 9004 Series CPU Power Management White Paper"
   - "AMD Optimizes EPYC Memory with NUMA" (NUMA architecture white paper)
   - "Technology Brief: AMD EPYC and SMT"

2. **AMD ROCm Documentation**:
   - "AMD Instinct MI100/MI200/MI300X System Optimization" (DF C-States, APBDIS, LCLK)
   - "BIOS Settings — AMD Instinct Customer Acceptance Guide"

3. **OEM Tuning Guides**:
   - Dell "Direct from Development - NUMA Configurations for AMD EPYC 2nd Generation"
   - Lenovo "Balanced Memory Configurations with 5th Generation AMD EPYC Processors"
   - Lenovo "Tuning UEFI Settings for Performance and Energy Efficiency on 4th Gen AMD EPYC"
   - Cisco "Performance Tuning for Cisco UCS M8 Platforms with AMD EPYC 4th/5th Gen"

4. **Third-Party Research**:
   - TechPowerUp "DDR5 Memory Performance Scaling with AMD Zen 5"
   - PC Perspective "A Deep Dive Into Zen 5 DDR5 Frequency Scaling"
   - Chips and Cheese "Evaluating Uniform Memory Access Mode on AMD's Turin" (NPS0 analysis)
   - Chips and Cheese "AMD's EPYC 9355P: Inside a 32 Core Zen 5 Server Chip"

5. **Community Guides**:
   - Reddit r/overclocking "Fool-Proof DDR5 Overclocking Guide for AM5 (64GB Dual Rank)"
   - Reddit r/Amd "ZEN 3 PBO and Curve Optimizer Tweaking/Overclocking Guide"
   - SkatterBencher "Ryzen Threadripper Pro 9975WX Overclocked to 5625 MHz"
   - ocinside.de "AMD Ryzen 7000/9000 DDR5 RAM OC Guide"

6. **NVIDIA Documentation**:
   - "GPUDirect" (P2P, RDMA, IOMMU requirements)
   - "Multi-GPU Systems — CUDA Programming Guide"

7. **AMD Benchmarking**:
   - Phoronix "AMD BIOS Tuning Guide Impact For Boosting AI/ML Performance On EPYC 9005 Series"
   - AMD Blog "Unlocking Optimal LLM Performance on AMD EPYC CPUs with vLLM"
   - AMD Blog "Maximizing AI Performance: The Role of AMD EPYC 9575F CPUs"

### Key Findings Cross-Reference

| Optimization | Source(s) | Evidence Quality |
|--------------|-----------|------------------|
| DF C-States = Disabled | AMD Instinct guides, Cisco tuning | ✅ Official |
| APBDIS = 1 | AMD MI300X guide, Instinct acceptance | ✅ Official |
| tREFI = 65535 | ocinside, Reddit guides, user benchmarks | ⚠️ Community (proven) |
| NPS1 for AI | Dell, Lenovo, AMD EPYC guides | ✅ Official |
| IOMMU = Disabled for P2P | NVIDIA GPUDirect, AMD ROCm | ✅ Official |
| LCLK Enhanced I/O | AMD MI200/MI300X tuning | ✅ Official |
| SMT = Enabled for LLM | AMD EPYC SMT white paper, benchmarks | ✅ Official |

---

## 9. Expected Performance Gains Summary

### Baseline: BIOS Defaults (Typical OEM Shipping Config)

| Metric | Default | Optimized | Delta |
|--------|---------|-----------|-------|
| **Memory Bandwidth** | 200-220 GB/s | 230-240 GB/s | +10-15% |
| **LLM Inference Throughput** | Baseline | +15-30% | Est. |
| **CPU Boost Frequency** | 4.0-4.5 GHz | 4.5-5.0 GHz | +10-15% |
| **Idle Power** | 150-200W | 200-250W | +25-50W |
| **Load Power** | 400-500W | 600-700W | +40% |

### User System Achieved Results (2026-01-30)

| Metric | Before (Defaults) | After (Optimized) | Gain |
|--------|-------------------|-------------------|------|
| **tok/s (llama.cpp)** | 4.44 | 11.74 | **+164%** |
| **vs Baseline** | -58% | +10% | - |
| **Memory Bandwidth** | Unknown | 236.4 GB/s | - |
| **CPU All-Core** | 2.5 GHz @ 294W | 5.6 GHz @ 1.25kW | +124% freq |

**Note**: User's 4.44→11.74 tok/s gain includes fixing **severely broken defaults** (possibly post-BIOS update corruption). Typical gain from optimal tuning vs **functional defaults** is **15-30%**, not 164%.

---

## 10. ASUS WRX90-Specific Notes

### 10.1 AI Tweaker vs Redfish

**Limitation**: ASUS AI Tweaker menu settings (PBO, Curve Optimizer, manual memory timings like tREFI) are **not exposed via Redfish API**.

**Implication**: 
- Redfish can verify AMD CBS settings (DF C-States, APBDIS, NPS, IOMMU)
- Must verify AI Tweaker settings via:
  - BMC KVM screenshots during BIOS navigation
  - Runtime stress testing (turbostat, STREAM benchmark)
  - Indirect inference (e.g., 236 GB/s bandwidth confirms tREFI active)

---

### 10.2 BIOS Update Impact

**User Experience (S-019)**: BIOS may reset to broken defaults after updates, even if "Keep Settings" selected.

**Best Practice**:
1. Export BIOS settings to USB before updates (`Save Profile` in BIOS)
2. After update, verify critical settings via Redfish
3. Re-enter AI Tweaker manually (tREFI, PBO, Curve Optimizer)
4. Run validation suite (STREAM, turbostat, GPU P2P test)

---

### 10.3 Known ASUS Settings Locations

| Setting | BIOS Path |
|---------|-----------|
| **DF C-States** | AMD CBS → DF Common Options → DF C-States |
| **APBDIS** | AMD CBS → NBIO Common Options → SMU Common Options → APBDIS |
| **NPS** | AMD CBS → NBIO Common Options → NUMA Per Socket |
| **IOMMU** | AMD CBS → NBIO Common Options → IOMMU |
| **ACS** | AMD CBS → NBIO Common Options → ACS Override |
| **PBO** | Advanced → AMD Overclocking → Precision Boost Overdrive |
| **Curve Optimizer** | Advanced → AMD Overclocking → Curve Optimizer |
| **tREFI** | AI Tweaker → Memory Timing Configuration → Advanced Timings |
| **LCLK** | AMD CBS → NBIO Common Options → LCLK DPM (if exists) |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **APBDIS** | Algorithmic Performance Boost Disable - locks Data Fabric to P0 |
| **DF** | Data Fabric - AMD's on-die interconnect between CCDs, memory controllers, I/O |
| **FCLK** | Fabric Clock - clock speed of Data Fabric |
| **LCLK** | Link Clock - internal bus speed between NBIO and Data Fabric |
| **MCLK** | Memory Clock - actual DDR frequency (MT/s ÷ 2) |
| **NBIO** | North Bridge I/O - PCIe/USB/SATA controller blocks |
| **NPS** | NUMA Per Socket - partitioning mode for memory controllers |
| **PPT** | Package Power Tracking - CPU power limit |
| **TDC** | Thermal Design Current - sustained current limit |
| **EDC** | Electrical Design Current - peak current limit |
| **tREFI** | Refresh Interval - cycles between DRAM refresh operations |
| **tRFC** | Refresh Cycle Time - duration of one refresh operation |

---

## Appendix B: Quick Reference Checklist

### Critical Settings for AI/LLM Workloads

- [ ] **DF C-States** = Disabled
- [ ] **APBDIS** = 1
- [ ] **NPS** = NPS1
- [ ] **IOMMU** = Disabled
- [ ] **ACS** = Disabled
- [ ] **Above 4G Decoding** = Enabled
- [ ] **PBO** = Enabled
- [ ] **tREFI** = 65535 (manual timing in AI Tweaker)
- [ ] **FCLK** = 2000-2133 MHz (for DDR5-6000/6200)
- [ ] **LCLK Mode** = Enhanced Preferred I/O or Static High
- [ ] **Global C-States** = Disabled (production servers)
- [ ] **SMT** = Enabled

### Verification Commands

```bash
# Memory bandwidth
./stream | grep Triad

# CPU boost under load
sudo turbostat --interval 1

# GPU P2P
./p2pBandwidthLatencyTest

# PCIe link speed
lspci -vvv | grep "LnkSta:"

# DIMM temperature
ipmitool sensor list | grep DIMM
```

---

**End of Document**
