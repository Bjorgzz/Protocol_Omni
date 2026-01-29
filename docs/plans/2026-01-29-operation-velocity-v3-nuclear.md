# Operation Velocity v3: NUCLEAR Overclocking - 13°C Chiller Edition

**Version**: 3.0 NUCLEAR  
**Date**: 2026-01-29  
**Author**: Fahad (The Executive Architect)  
**Status**: APPROVED FOR EXECUTION  
**Cooling**: 13°C Liquid Chiller (Sub-Ambient) on CPU + RTX 5090

---

## Executive Summary

Push the Threadripper PRO 9995WX to **1400W** (USER PROVEN, R23 stable) and RTX 5090 to **750W @ 3200MHz** using aggressive 13°C chiller cooling. Memory running **tREFI 65535** (USER PROVEN stable). This is not conservative overclocking — this is maximum extraction.

**Target**: >13 tok/s inference throughput for DeepSeek-R1-0528

| Component | Stock | **NUCLEAR** |
|-----------|-------|-------------|
| CPU Power | 350W TDP | **1400W** |
| CPU Clock | 2.5 GHz base | **5.5+ GHz** all-core |
| RTX 5090 Power | 575W | **750W** |
| RTX 5090 Clock | 2407 MHz boost | **3200 MHz** sustained |
| Memory Refresh | tREFI 12000 | **tREFI 65535** |
| Memory Timings | 40-40-40-80 | **34-34-34-68** |

---

## Hardware Configuration (VERIFIED)

| Position | Component | Spec | Max Power | Cooling |
|----------|-----------|------|-----------|---------|
| CPU | AMD Threadripper PRO 9995WX | 96C/192T Zen5 | 350W TDP / **1400W PROVEN** | **Liquid Chiller 13°C** |
| GPU 0 | RTX PRO 6000 Blackwell | 96GB GDDR7 ECC | 600W | Air (stock) |
| GPU 1 | RTX 5090 | 32GB GDDR7 | 575W → **750W** | **Liquid Chiller 13°C** |
| RAM | SK Hynix HMCGY4MHBRB489N | 384GB DDR5-6000 ECC RDIMM | 1.1V **LOCKED** | Chiller Ambient (~20°C) |

### Critical Hardware Constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| **PMIC Voltage Lock** | RAM stuck at 1.1V | Timing-only optimization |
| **UCLK DIV1 Missing** | Memory controller at half speed | Cannot sync 1:1, use 2:1 |
| **RTX 5090 Cold Bug** | GPU crashes below -10°C | Keep chiller **>5°C** |
| **PRO 6000 No Chiller** | Cannot push beyond 600W | Focus chiller budget on 5090 |

---

## Phase 0: Pre-Flight Safety Checks

### 0.1 Verify Chiller Temperature Limits

```bash
# CRITICAL: RTX 5090 cold bug threshold
# Set chiller target to 10-15°C (NOT sub-zero!)
# Below -10°C = GPU black screen, system hang

# Verify current chiller setpoint
ssh omni@100.94.47.77 << 'EOF'
echo "=== Chiller Status ==="
# Check if chiller controller is accessible
# (Adjust command based on your chiller model)
cat /sys/class/hwmon/hwmon*/temp*_input 2>/dev/null || echo "No direct chiller readout"

echo "=== GPU Temperature Baseline ==="
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits
EOF
```

### 0.2 Verify Current System State

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== BIOS Settings Verification ==="
# PBO Status
cat /sys/devices/system/cpu/cpu0/cpufreq/boost
lscpu | grep -E "MHz|CPU\(s\)"

echo "=== GPU Configuration ==="
nvidia-smi --query-gpu=index,name,power.limit,clocks.current.graphics --format=csv

echo "=== Memory Configuration ==="
sudo dmidecode -t memory | grep -E "Speed|Voltage|Manufacturer"

echo "=== NUMA Topology ==="
numactl --hardware | head -5

echo "=== Current Inference Baseline ==="
curl -s http://localhost:8000/health
EOF
```

---

## Phase 1: CPU Extreme Optimization

### 1.1 Precision Boost Overdrive - Maximum Aggression

**BIOS Path**: Advanced → AMD Overclocking → Precision Boost Overdrive

| Setting | Conservative | **NUCLEAR (13°C Chiller)** | Rationale |
|---------|--------------|------------------------------|-----------|
| PBO Mode | Enabled | **Advanced** | Unlocks per-CCD/CO controls |
| PPT Limit | 350W | **1400W** | **USER PROVEN** - R23 stable |
| TDC Limit | 280A | **1000A** | Sustained current for 1400W |
| EDC Limit | 420A | **1400A** | Peak current headroom |
| Scalar | Auto | **10x** | Maximum boost duration |
| Thermal Throttle | 95°C | **85°C** | Reasonable safety margin with chiller |

### 1.2 Curve Optimizer - Per-Core Optimization

**BIOS Path**: Advanced → AMD Overclocking → Curve Optimizer

**Strategy**: Zen5 silicon varies. Map cores first, then apply graduated offsets.

#### Step 1: Map Silicon Quality

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== CPPC Preferred Core Ranking ==="
for i in $(seq 0 191); do
    perf=$(cat /sys/devices/system/cpu/cpu$i/acpi_cppc/highest_perf 2>/dev/null)
    echo "CPU$i: $perf"
done | sort -t: -k2 -rn | head -20 > /tmp/cppc_ranking.txt
cat /tmp/cppc_ranking.txt
EOF
```

#### Step 2: Apply Graduated Offsets

Based on CPPC ranking, categorize cores:

| Tier | CPPC Score | Count (est.) | Curve Offset | Rationale |
|------|------------|--------------|--------------|-----------|
| **Platinum** | 200+ | ~12 cores | **-50** | Best silicon, max undervolt |
| **Gold** | 190-199 | ~24 cores | **-45** | Strong cores, aggressive |
| **Silver** | 180-189 | ~36 cores | **-40** | Average cores |
| **Bronze** | <180 | ~24 cores | **-35** | Weakest cores, still pushed |

**BIOS Settings**:
- Curve Optimizer: **Per Core**
- Apply offsets per the CPPC mapping above
- Sign: **Negative** (undervolt = cooler + faster)

### 1.3 Advanced SMU Tuning (AI OPTIMIZED)

**BIOS Path**: Advanced → AMD CBS → SMU Common Options

| Setting | Value | Why (AI Workload) |
|---------|-------|-------------------|
| CPPC | **Enabled** | Allows OS to prefer best cores |
| CPPC Preferred Cores | **Enabled** | Improves scheduling for mixed workloads |
| Global C-State Control | **Disabled** | Latency penalty on wake - AI needs consistent response |
| Power Supply Idle Control | **Typical Current Idle** | Lower latency than Low Current |
| DF C-States | **Disabled** | **CRITICAL FOR AI**: Data Fabric P-states add latency to memory access |
| APBDIS | **1** | **CRITICAL**: Disables Data Fabric P-states completely |
| Determinism Control | **Manual** | Enables deterministic performance |
| Determinism Slider | **Power** | Prioritizes sustained throughput over burst |

**WHY DF C-States DISABLED**: LLM inference is memory-bandwidth bound. Data Fabric sleep states add ~100-500ns wake latency on every memory access. With 671B model streaming weights, this compounds to significant slowdown.

### 1.4 Infinity Fabric Optimization (AI BANDWIDTH PRIORITY)

**BIOS Path**: Advanced → AMD CBS → DF Common Options

| Setting | Value | Rationale |
|---------|-------|-----------|
| FCLK Frequency | **2100 MHz** | ASUS AI Cache Boost default - max bandwidth |
| UCLK DIV1 Mode | **N/A** | Not available on TR 9000 series |
| Memory Interleaving | **Channel** | Maximizes bandwidth for sequential reads |
| Memory Interleaving Size | **2KB** | Optimal for LLM weight streaming patterns |
| DRAM Scrub Time | **Disabled** | Eliminates background memory overhead |
| Redirect Scrubber Control | **Disabled** | No ECC scrubbing during inference |
| Disable DF Sync Flood Propagation | **Enabled** | Prevents cascade on non-fatal errors |

**NOTE**: FCLK 2100MHz at DDR5-6000 creates slight async (3000 MCLK vs 2100 FCLK). This is FINE - bandwidth gain outweighs latency penalty for AI workloads.

### 1.5 Power Management for Sustained AI Workloads

**BIOS Path**: Advanced → AMD CBS → CPU Common Options → Performance

| Setting | Value | Why (AI Workload) |
|---------|-------|-------------------|
| Core Performance Boost | **Enabled** | Allow maximum clocks |
| Global C-State Control | **Disabled** | (Redundant with SMU, but set both) |
| Power Management | **Maximum Performance** | Full power delivery to compute |
| cTDP Control | **Manual** | Unlock power limits |
| cTDP | **350W** (will be overridden by PBO) | Base thermal design |
| Package Power Limit | **1400W** | Match PBO PPT |
| PROCHOT | **Disabled** | We have chiller - no thermal throttle needed |

### 1.6 CPU Prefetcher Optimization (AI STREAMING)

**BIOS Path**: Advanced → AMD CBS → CPU Common Options → Prefetch Settings

Prefetchers are **CRITICAL** for AI workloads. LLM inference streams weights sequentially - aggressive prefetching keeps the pipeline fed.

| Setting | Stock | **AI NUCLEAR** | Rationale |
|---------|-------|----------------|-----------|
| L1 Stream HW Prefetcher | Auto | **Enabled** | Sequential read prefetch - AI CRITICAL |
| L1 Stride Prefetcher | Auto | **Enabled** | Strided access patterns in tensor ops |
| L1 Region Prefetcher | Auto | **Enabled** | Spatial locality for weight blocks |
| L1 Burst Prefetch Mode | Auto | **Enabled** | Burst access for GGUF streaming |
| L2 Stream HW Prefetcher | Auto | **Enabled** | L2 sequential prefetch |
| L2 Up/Down Prefetcher | Auto | **Enabled** | Bidirectional scan patterns |

**Redfish Attributes:**
```
CbsCmnCpuL1StreamHwPrefetcherSHP → Enabled
CbsCmnCpuL1StridePrefetcherSHP → Enabled
CbsCmnCpuL1RegionPrefetcherSHP → Enabled
CbsCmnCpuL1BurstPrefetchModeSHP → Enabled
CbsCmnCpuL2StreamHwPrefetcherSHP → Enabled
CbsCmnCpuL2UpDownPrefetcherSHP → Enabled
```

**WHY ALL ENABLED**: Unlike gaming (random access, cache thrashing), AI inference has predictable sequential access patterns. Aggressive prefetching reduces memory latency by pre-loading weights before they're needed.

---

## Phase 2: Memory Timing Optimization (AI BANDWIDTH PRIORITY)

### 2.1 AI Workload Memory Characteristics

**CRITICAL INSIGHT**: LLM inference is **memory bandwidth bound**, NOT latency bound.

| Workload Type | Priority | Why |
|---------------|----------|-----|
| Gaming | Latency > Bandwidth | Random access patterns, cache hits matter |
| **AI/LLM Inference** | **Bandwidth > Latency** | Sequential weight streaming, massive data volume |

**For DeepSeek-R1 671B:**
- Model weights = ~377GB (Q4_K_M)
- Each token requires streaming majority of weights
- At 13 tok/s target, we need 4.9+ TB/s sustained read bandwidth
- DDR5-6000 theoretical: ~460 GB/s → GPU memory becomes bottleneck

**Implication**: Optimize for SUSTAINED BANDWIDTH, not first-word latency.

### 2.2 Constraints Acknowledgment

**HARD LIMITS (CANNOT BE CHANGED):**
- Voltage: **1.1V LOCKED** (SK Hynix RDIMM PMIC)
- Speed: **6000 MT/s** (rated 6400 MT/s but not achieving)
- UCLK: **1500 MHz** (2:1 ratio, not 1:1)

**PMIC BYPASS ATTEMPT** (Low Probability of Success):
If available in your BIOS (Ai Tweaker or Advanced → AMD Overclocking):
- Look for **"Enable Platform PMIC Control"** → Try **Enabled**
- Look for **"High Voltage Mode"** → Try **Enabled**
- Look for **"Tweaker's Paradise"** submenu

*Note: Most RDIMM PMICs are hardware-locked. These settings exist for consumer DIMMs. Worth checking but expect no change.*

**CAN OPTIMIZE:**
- Primary timings (tCL, tRCD, tRP, tRAS) - moderate impact
- **Secondary timings (tRFC, tREFI)** - HIGH impact for bandwidth
- Tertiary timings (tFAW, tWR, tRTP) - controls burst patterns

### 2.3 Memory Timing Configuration (AI OPTIMIZED)

**BIOS Path**: Advanced → AMD CBS → UMC Common Options → DDR5 Timing Configuration

**Philosophy**: Slightly loosen CL if it helps tRFC/tREFI - bandwidth wins for AI.

| Timing | Stock | **AI NUCLEAR** | Impact on AI |
|--------|-------|----------------|--------------|
| tCL | 40 | **34** | Minor - first word only |
| tRCD | 40 | **34** | Minor - row activation |
| tRP | 40 | **34** | Minor - precharge |
| tRAS | 80 | **68** | Minor - row access time |
| tRC | 120 | **102** | Medium - cycle time |
| tWR | 72 | **42** | High - write completion |
| tRTP | 16 | **10** | High - read-to-precharge |
| tFAW | 32 | **16** | **CRITICAL** - four activate window, unlocks burst |

### 2.4 tREFI/tRFC (BANDWIDTH MULTIPLIER)

**User has validated tREFI 65535 stable** with 13°C chiller keeping DIMMs cold.

**WHY tREFI 65535 IS PERFECT FOR AI**:
- Refresh cycles BLOCK memory bandwidth
- Stock tREFI ~12000 = refresh every 12000 cycles
- tREFI 65535 = refresh every 65535 cycles = **5.5x fewer interruptions**
- With cold DIMMs, data retention is not at risk

| Timing | Stock | **AI NUCLEAR** | Bandwidth Impact |
|--------|-------|----------------|------------------|
| tREFI | ~12000 | **65535** | **+15-20% effective bandwidth** |
| tRFC | ~560 | **420** | **Faster refresh = less blocked time** |
| tRFC2 | Auto | **320** | Faster secondary refresh |
| tRFCsb | Auto | **240** | Same-bank refresh |

**NOTE**: DIMMs stay ~20-25°C with ambient chiller cooling. No thermal concern.

### 2.5 Tertiary Timings (BURST OPTIMIZATION)

These timings control back-to-back operation efficiency. Critical for AI's sequential streaming patterns.

**BIOS Path**: Advanced → AMD CBS → UMC Common Options → DDR5 Timing Configuration

| Timing | Stock | **AI NUCLEAR** | Impact on AI |
|--------|-------|----------------|--------------|
| tCWL | Auto | **32** | CAS Write Latency - minor for read-heavy AI |
| tRRD_S | Auto | **4** | Row-to-row same bank group - burst access |
| tRRD_L | Auto | **6** | Row-to-row different bank group |
| tWTR_S | Auto | **4** | Write-to-read same bank group |
| tWTR_L | Auto | **12** | Write-to-read different bank group |

### 2.6 Read/Write Turnaround (SEQUENTIAL BANDWIDTH)

These control back-to-back read/write efficiency. **Critical for AI** which does massive sequential reads.

| Timing | Stock | **AI NUCLEAR** | Impact on AI |
|--------|-------|----------------|--------------|
| tRDRD_Sc | Auto | **1** | Read-to-read same DIMM/channel - **HIGH** |
| tRDRD_Sd | Auto | **4** | Read-to-read same DIMM different bank |
| tRDRD_Dd | Auto | **4** | Read-to-read different DIMM |
| tWRWR_Sc | Auto | **1** | Write-to-write same channel |
| tWRWR_Sd | Auto | **4** | Write-to-write same DIMM different bank |
| tWRWR_Dd | Auto | **4** | Write-to-write different DIMM |
| tRDWR | Auto | **8** | Read-to-write turnaround |
| tWRRD | Auto | **2** | Write-to-read same rank |

**WHY tRDRD_Sc=1 MATTERS**: LLM weight streaming is predominantly read operations. Minimizing read-to-read delay directly impacts token generation bandwidth.

### 2.7 Redfish Attribute Mapping (FOR REMOTE CONFIGURATION)

These are the exact Redfish attribute names for automation:

```
# Primary Timings
CbsCmnMemTimingTclCtrlDdrSHP → Manual, CbsCmnMemTimingTclDdrSHP → 34
CbsCmnMemTimingTrcdCtrlDdrSHP → Manual, CbsCmnMemTimingTrcdDdrSHP → 34
CbsCmnMemTimingTrpCtrlDdrSHP → Manual, CbsCmnMemTimingTrpDdrSHP → 34
CbsCmnMemTimingTrasCtrlDdrSHP → Manual, CbsCmnMemTimingTrasDdrSHP → 68

# Secondary Timings
CbsCmnMemTimingTrcCtrlDdrSHP → Manual, CbsCmnMemTimingTrcDdrSHP → 102
CbsCmnMemTimingTwrCtrlDdrSHP → Manual, CbsCmnMemTimingTwrDdrSHP → 42
CbsCmnMemTimingTrtpCtrlDdrSHP → Manual, CbsCmnMemTimingTrtpDdrSHP → 10
CbsCmnMemTimingTfawCtrlDdrSHP → Manual, CbsCmnMemTimingTfawDdrSHP → 16

# Refresh Timings (CRITICAL FOR AI BANDWIDTH)
CbsCmnMemTimingTrfc1CtrlDdrSHP → Manual, CbsCmnMemTimingTrfc1DdrSHP → 420
CbsCmnMemTimingTrfc2CtrlDdrSHP → Manual, CbsCmnMemTimingTrfc2DdrSHP → 320
CbsCmnMemTimingTrfcSbCtrlDdrSHP → Manual, CbsCmnMemTimingTrfcSbDdrSHP → 240
# tREFI requires BIOS - not exposed as numeric in Redfish

# Turnaround Timings
CbsCmnMemTimingTrdrdScCtrlDdrSHP → Manual, CbsCmnMemTimingTrdrdScDdrSHP → 1
CbsCmnMemTimingTrdrdSdCtrlDdrSHP → Manual, CbsCmnMemTimingTrdrdSdDdrSHP → 4
CbsCmnMemTimingTrdrdDdCtrlDdrSHP → Manual, CbsCmnMemTimingTrdrdDdDdrSHP → 4
CbsCmnMemTimingTwrwrScCtrlDdrSHP → Manual, CbsCmnMemTimingTwrwrScDdrSHP → 1
CbsCmnMemTimingTwrwrSdCtrlDdrSHP → Manual, CbsCmnMemTimingTwrwrSdDdrSHP → 4
CbsCmnMemTimingTwrwrDdCtrlDdrSHP → Manual, CbsCmnMemTimingTwrwrDdDdrSHP → 4
CbsCmnMemTimingTrdwrCtrlDdrSHP → Manual, CbsCmnMemTimingTrdwrDdrSHP → 8
CbsCmnMemTimingTwrrdCtrlDdrSHP → Manual, CbsCmnMemTimingTwrrdDdrSHP → 2

# Row Timings
CbsCmnMemTimingTrrdSCtrlDdrSHP → Manual, CbsCmnMemTimingTrrdSDdrSHP → 4
CbsCmnMemTimingTrrdLCtrlDdrSHP → Manual, CbsCmnMemTimingTrrdLDdrSHP → 6

# Write-to-Read Timings
CbsCmnMemTimingTwtrSCtrlDdrSHP → Manual, CbsCmnMemTimingTwtrSDdrSHP → 4
CbsCmnMemTimingTwtrLCtrlDdrSHP → Manual, CbsCmnMemTimingTwtrLDdrSHP → 12
```

### 2.8 Memory Bandwidth Validation (AI BENCHMARK)

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== MEMORY BANDWIDTH TEST (AI WORKLOAD PROXY) ==="

# STREAM benchmark - measures sustained bandwidth
git clone https://github.com/jeffhammond/STREAM.git /tmp/stream 2>/dev/null || true
cd /tmp/stream
gcc -O3 -march=native -fopenmp -DSTREAM_ARRAY_SIZE=500000000 stream.c -o stream
OMP_NUM_THREADS=192 ./stream

echo ""
echo "=== EXPECTED RESULTS FOR AI-OPTIMIZED SETTINGS ==="
echo "Copy:  > 400 GB/s (stock ~350 GB/s)"
echo "Scale: > 400 GB/s"
echo "Add:   > 420 GB/s"
echo "Triad: > 420 GB/s"
echo ""
echo "If below these numbers, check:"
echo "  1. FCLK at 2100 MHz"
echo "  2. DF C-States DISABLED"
echo "  3. Memory Interleaving = Channel"
EOF
```

---

## Phase 2.5: PCIe P2P Optimization (CRITICAL FOR MULTI-GPU AI)

### Why PCIe P2P Matters for AI Inference

With tensor split across RTX PRO 6000 (96GB) + RTX 5090 (32GB), weights transfer between GPUs constantly. Default BIOS settings route GPU-GPU traffic through CPU, adding latency.

**Direct P2P Path**: GPU → PCIe Switch → GPU (1-2μs)
**CPU-Routed Path**: GPU → PCIe → CPU → IOMMU → PCIe → GPU (5-10μs)

For pipeline parallelism at 13 tok/s, we need direct P2P.

### BIOS Settings for P2P Optimization

**BIOS Path**: Advanced → AMD CBS → NBIO Common Options

| Setting | Value | Why (AI Workload) |
|---------|-------|-------------------|
| IOMMU | **Disabled** | **CRITICAL**: Removes CPU routing overhead |
| ACS Enable | **Disabled** | Allows direct P2P between PCIe devices |
| PCIe ARI Support | **Enabled** | Alternative Routing-ID for large BAR |
| Above 4G Decoding | **Enabled** | Large BAR support (REQUIRED) |
| Re-Size BAR Support | **Enabled** | Full GPU memory mapping |
| SR-IOV Support | **Disabled** | Only needed for virtualization |

**BIOS Path**: Advanced → AMD CBS → NBIO Common Options → PCIe Configuration

| Setting | Value | Why |
|---------|-------|-----|
| PCIe Link Speed | **Gen5** | Maximum bandwidth (32 GT/s per lane) |
| PCIe x16 Slot 1 | **Gen5 x16** | PRO 6000 Blackwell slot |
| PCIe x16 Slot 2 | **Gen5 x16** | RTX 5090 slot |
| ASPM | **Disabled** | No power management latency |
| PCIe Relaxed Ordering | **Enabled** | Better throughput for large transfers |

### Verify P2P is Working

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== PCIe P2P STATUS CHECK ==="

# Check if IOMMU is disabled
dmesg | grep -i iommu | head -5
cat /proc/cmdline | grep -o "iommu=[^ ]*" || echo "IOMMU: Not in cmdline (good)"

# Check GPU P2P capabilities
nvidia-smi topo -m

echo ""
echo "EXPECTED OUTPUT:"
echo "  GPU0 <-> GPU1: PHB or PIX (direct PCIe)"
echo "  If shows 'SYS' or 'NODE', IOMMU is routing through CPU"
echo ""
echo "For maximum bandwidth, you want PHB (same PCIe host bridge) or PIX (same PCIe switch)"
EOF
```

---

## Phase 3: GPU Optimization (AI INFERENCE PRIORITY)

### 3.0 GPU Optimization Philosophy for AI

**CRITICAL INSIGHT**: For LLM inference, memory bandwidth > compute frequency.

| Setting | Gaming Priority | **AI Inference Priority** |
|---------|----------------|---------------------------|
| Core Clock | Maximum | High (but not max) |
| **Memory Clock** | Moderate | **MAXIMUM** |
| Power Limit | High | **MAXIMUM** (sustained throughput) |
| Temp Target | Low | Moderate OK (we have chiller) |

**Why Memory Clock Matters More**:
- LLM inference streams weights from VRAM to tensor cores
- RTX 5090 GDDR7: 1792 GB/s theoretical bandwidth
- Pushing memory clock +2000 MHz = ~+11% bandwidth
- Core clock headroom is less impactful for bandwidth-bound workloads

### 3.1 RTX PRO 6000 Blackwell (GPU 0) - AI Optimized

**Constraint**: No liquid chiller on this GPU, keep within thermal limits.

```bash
#!/bin/bash
# gpu_oc_pro6000_ai.sh - AI-optimized settings for air-cooled GPU

# Enable persistence mode (REQUIRED for inference servers)
nvidia-smi -i 0 -pm 1

# Set compute mode to Exclusive Process (one inference server owns GPU)
nvidia-smi -i 0 -c EXCLUSIVE_PROCESS

# Power limit: Already at max (600W)
nvidia-smi -i 0 -pl 600

# Clock targets: Prioritize stability over peak for 96GB workstation card
# Memory bandwidth matters more than core clock for AI
nvidia-smi -i 0 -lgc 2100,2550

# Disable auto boost to reduce variance (optional - may not be supported on all drivers)
nvidia-smi -i 0 --auto-boost-default=DISABLED 2>/dev/null || echo "Note: auto-boost control not supported on this driver"

echo "PRO 6000 AI-optimized: 600W, 2100-2550MHz, Exclusive Mode"
```

### 3.2 RTX 5090 (GPU 1) - NUCLEAR AI MODE with 13°C Liquid Chiller

**Unlocked by 13°C Liquid Chiller**:
- Die temps stay ~30-40°C under full load
- Memory clock can be pushed HARD (GDDR7 loves cold)
- Core clock 3200+ MHz sustainable
- Power limit 750W for sustained tensor throughput

```bash
#!/bin/bash
# gpu_oc_5090_ai_nuclear.sh - Maximum AI throughput for 13°C chilled GPU

# Enable persistence mode (REQUIRED)
nvidia-smi -i 1 -pm 1

# Set compute mode to Exclusive Process
nvidia-smi -i 1 -c EXCLUSIVE_PROCESS

# Power limit: 750W for sustained AI workload (no throttling with chiller)
nvidia-smi -i 1 -pl 750

# Core clock: High but not bleeding edge - stability matters
nvidia-smi -i 1 -lgc 2500,3150

# MEMORY CLOCK IS THE KEY FOR AI - push it hard
# +2000 MHz offset on GDDR7 with 13°C water is achievable
# This is where the real AI gains come from
#
# NOTE: Memory clock offset requires nvidia-settings (X11) or NVML API
# For headless servers, options are:
#   1. nvidia-settings via X virtual framebuffer: Xvfb :0 & DISPLAY=:0 nvidia-settings -a "[gpu:1]/GPUMemoryTransferRateOffset[3]=2000"
#   2. Use nvidia-smi memory clock lock instead (less flexible but headless-compatible):
nvidia-smi -i 1 -lmc 2200,2200  # Lock memory at high stable frequency

# Disable auto boost for consistent benchmarks (optional - may not be supported)
nvidia-smi -i 1 --auto-boost-default=DISABLED 2>/dev/null || echo "Note: auto-boost control not supported on this driver"

echo "RTX 5090 AI NUCLEAR: 750W, 2500-3150MHz core, memory locked high"
```

**CHILLER STATUS AT 13°C:**
```
Your chiller setpoint: 13°C ✓
Cold bug threshold: -10°C to -20°C
Margin: ~25°C headroom - COMPLETELY SAFE
```

### 3.3 Tensor Split Optimization (AI WORKLOAD)

**Current Analysis**:
- PRO 6000: 96GB @ 1120 GB/s bandwidth
- RTX 5090: 32GB @ 1792 GB/s bandwidth (FASTER per-byte!)

The 5090 has **60% higher bandwidth density**. For AI, we want to leverage this.

| GPU | VRAM | Bandwidth | Current Split | **AI Optimized** |
|-----|------|-----------|---------------|------------------|
| PRO 6000 | 96GB | 1120 GB/s | 75 | **65** |
| RTX 5090 | 32GB | 1792 GB/s | 25 | **35** |

The liquid-chilled 5090 with higher bandwidth should handle more work.

**llama.cpp launch parameter update**:
```bash
--tensor-split 65,35
```

### 3.4 GPU Driver Settings for AI Inference

```bash
ssh omni@100.94.47.77 << 'EOF'
# Ensure maximum performance mode
nvidia-smi -pm 1  # Persistence mode

# Set power limits per GPU (explicit values required)
nvidia-smi -i 0 -pl 600  # PRO 6000: 600W (air cooled max)
nvidia-smi -i 1 -pl 750  # RTX 5090: 750W (liquid chilled)

# Check ECC is enabled (REQUIRED for AI reliability)
nvidia-smi --query-gpu=ecc.mode.current --format=csv

# Set compute mode 
nvidia-smi -c EXCLUSIVE_PROCESS

# Verify configuration
nvidia-smi --query-gpu=index,name,power.limit,clocks.current.graphics,clocks.current.memory,compute_mode --format=csv
EOF
```

---

## Phase 4: Complete BIOS Configuration Checklist

### 4.1 Advanced Tab → AMD Overclocking

| Setting | Value |
|---------|-------|
| Accept AMD Overclocking Disclaimer | **Accept** |
| Precision Boost Overdrive | **Advanced** |
| PPT Limit [W] | **1400** |
| TDC Limit [A] | **1000** |
| EDC Limit [A] | **1400** |
| Precision Boost Overdrive Scalar | **10X** |
| Max CPU Boost Clock Override | **+200 MHz** |
| Platform Thermal Throttle Limit | **85** |
| Curve Optimizer | **Per Core** |
| [Apply per-core offsets: -50/-45/-40/-35] | |

### 4.2 Advanced Tab → AMD CBS → CPU Common Options (AI OPTIMIZED)

| Setting | Value | AI Rationale |
|---------|-------|--------------|
| Core Performance Boost | **Enabled** | Maximum clocks |
| Global C-State Control | **Disabled** | **AI CRITICAL**: Eliminates wake latency |
| Power Supply Idle Control | **Typical Current Idle** | Lower latency than Low Current |
| SEV-SNP | **Disabled** | Not needed, saves overhead |
| SMEE | **Disabled** | Not needed, saves overhead |

### 4.3 Advanced Tab → AMD CBS → CPU Common Options → Prefetch (AI STREAMING)

| Setting | Value | AI Rationale |
|---------|-------|--------------|
| L1 Stream HW Prefetcher | **Enabled** | Sequential weight streaming |
| L1 Stride Prefetcher | **Enabled** | Tensor operation patterns |
| L1 Region Prefetcher | **Enabled** | Weight block locality |
| L1 Burst Prefetch Mode | **Enabled** | GGUF burst access |
| L2 Stream HW Prefetcher | **Enabled** | L2 sequential prefetch |
| L2 Up/Down Prefetcher | **Enabled** | Bidirectional scanning |

### 4.4 Advanced Tab → AMD CBS → SMU Common Options (AI CRITICAL)

| Setting | Value | AI Rationale |
|---------|-------|--------------|
| CPPC | **Enabled** | OS core preference |
| CPPC Preferred Cores | **Enabled** | Better scheduling |
| DF C-States | **Disabled** | **AI CRITICAL**: Data Fabric sleep = bandwidth killer |
| APBDIS | **1** | **AI CRITICAL**: Fully disables DF P-states |
| Determinism Control | **Manual** | Enables slider |
| Determinism Slider | **Power** | Sustained throughput priority |

### 4.5 Advanced Tab → AMD CBS → DF Common Options (AI BANDWIDTH)

| Setting | Value | AI Rationale |
|---------|-------|--------------|
| NUMA Nodes Per Socket | **NPS1** | Single NUMA domain |
| FCLK Frequency | **2100 MHz** | ASUS AI Cache Boost default |
| Memory Interleaving | **Channel** | **AI CRITICAL**: Max sequential bandwidth |
| Memory Interleaving Size | **2KB** | Optimal for weight streaming |
| DRAM Scrub Time | **Disabled** | No background overhead |
| Redirect Scrubber Control | **Disabled** | No ECC scrubbing during inference |
| Disable DF Sync Flood Propagation | **Enabled** | Prevents cascade on non-fatal |

### 4.6 Advanced Tab → AMD CBS → NBIO Common Options (P2P CRITICAL)

| Setting | Value | AI Rationale |
|---------|-------|--------------|
| IOMMU | **Disabled** | **AI CRITICAL**: Removes CPU routing for GPU P2P |
| ACS Enable | **Disabled** | **AI CRITICAL**: Allows direct GPU↔GPU transfer |
| PCIe ARI Support | **Enabled** | Large BAR support |
| Above 4G Decoding | **Enabled** | **REQUIRED** for multi-GPU |
| Re-Size BAR Support | **Enabled** | Full GPU memory mapping |
| SR-IOV Support | **Disabled** | Only for virtualization |
| ASPM | **Disabled** | No PCIe power management latency |
| PCIe Relaxed Ordering | **Enabled** | Better large transfer throughput |

### 4.7 Advanced Tab → AMD CBS → UMC Common Options (COMPREHENSIVE)

**All timings listed - reference Phase 2.3-2.7 for rationale.**

| Category | Timing | Value |
|----------|--------|-------|
| **Primary** | tCL | **34** |
| | tRCD | **34** |
| | tRP | **34** |
| | tRAS | **68** |
| | tRC | **102** |
| **Secondary** | tWR | **42** |
| | tRTP | **10** |
| | tFAW | **16** |
| | tCWL | **32** |
| **Refresh** | tREFI | **65535** (BIOS only) |
| | tRFC | **420** |
| | tRFC2 | **320** |
| | tRFCsb | **240** |
| **Row** | tRRD_S | **4** |
| | tRRD_L | **6** |
| **Turnaround** | tRDRD_Sc | **1** (AI CRITICAL) |
| | tRDRD_Sd | **4** |
| | tRDRD_Dd | **4** |
| | tWRWR_Sc | **1** |
| | tWRWR_Sd | **4** |
| | tWRWR_Dd | **4** |
| | tRDWR | **8** |
| | tWRRD | **2** |
| **Write-Read** | tWTR_S | **4** |
| | tWTR_L | **12** |

### 4.8 Boot Tab

| Setting | Value |
|---------|-------|
| Wait For F1 If Error | **Disabled** |
| Fast Boot | **Disabled** (for stability testing) |
| CSM Support | **Disabled** |
| Secure Boot | **Other OS** (disabled) |

### 4.9 Redfish vs Physical BIOS Access Summary

**Reference for remote vs manual configuration.**

| Setting Category | Redfish Access | Physical BIOS Required |
|------------------|----------------|------------------------|
| **CPU/SMU** | DF C-States, APBDIS, CPPC, Determinism | PBO PPT/TDC/EDC, Curve Optimizer, Thermal Limit |
| **Memory Timings** | All except tREFI | tREFI 65535 (numeric input) |
| **PCIe/NBIO** | IOMMU, ACS, ASPM, ReBAR | None |
| **Data Fabric** | Memory Interleaving, FCLK (limited) | FCLK fine-tuning (ASUS AI Cache Boost) |
| **Boot** | CSM, Secure Boot state | Fast Boot toggle |

**Execution Strategy:**
1. **Phase A (Remote)**: Apply all Redfish-accessible settings first
2. **Phase B (BMC KVM)**: During next reboot, set ASUS-specific: PBO 1400W, CO offsets, tREFI 65535

**Alternative: EFI Shell Scripted BIOS Modification**

For scriptable BIOS changes without KVM clicking, use open-source EFI tools:

**IFR Extraction Status: ✅ COMPLETE**
- BIOS 1203 IFR extracted → `tools/bios/wrx90_ifr_full.json` (2011 settings, 33,006 lines)
- AI-optimized offsets documented → `tools/bios/wrx90_ai_settings_analysis.md`
- EFI Shell script created → `tools/bios/nuclear_settings.nsh`

**Key VarStores:**
| VarID | Name | GUID | Purpose |
|-------|------|------|---------|
| 5 | Setup | EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9 | Main BIOS settings |
| 16 | AmdSetupSHP | 3A997502-647A-4C82-998E-52EF9486A247 | Zen5 TR 9000 CBS settings |

**Required Tools (all free/open-source):**
1. **setup_var.efi** - [github.com/datasone/setup_var.efi](https://github.com/datasone/setup_var.efi) - UEFI variable editor
2. **EFI Shell** - [github.com/tianocore/edk2](https://github.com/tianocore/edk2/releases) (Shell.efi)

**USB Preparation:**
```
USB Drive (FAT32):
├── EFI/
│   ├── BOOT/
│   │   └── BOOTX64.EFI    # Shell.efi renamed
│   └── Tools/
│       ├── setup_var.efi
│       └── nuclear_settings.nsh  # From tools/bios/
```

**AI-Critical Settings (from IFR extraction):**
```bash
# DF C-States = Disabled (offset 0x42D) **BANDWIDTH CRITICAL**
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# Global C-State = Disabled (offset 0x23)
setup_var.efi 0x23 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# IOMMU = Disabled (offset 0x377) **P2P CRITICAL**
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# ACS = Disabled (offset 0x341) **P2P CRITICAL**
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# PPT = 1400W (offset 0x418-0x41C, all 4 bytes)
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # Manual mode
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247  # 1400 = 0x0578 (byte 0)
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 1)
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 2)
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 3)

# TDP = 350W (offset 0x414-0x417, all 4 bytes)
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247  # 350 = 0x015E (byte 0)
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 1)
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 2)
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 3)

# All Prefetchers = Enabled (offsets 0x5D-0x62)
setup_var.efi 0x5D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Stream
setup_var.efi 0x5E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Stride
setup_var.efi 0x5F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Region
setup_var.efi 0x60 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L2 Stream
setup_var.efi 0x61 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L2 Up/Down
setup_var.efi 0x62 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Burst

# Above 4G Decoding - Setup VarStore (explicit GUID required)
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
```

**Execution via BMC KVM:**
```
1. Prepare USB with EFI Shell + setup_var.efi + nuclear_settings.nsh
2. Access BMC KVM (ssh tunnel: ssh -L 8443:192.168.3.202:443)
3. Reboot server → F8 (Boot Menu) → Select USB
4. In EFI Shell: fs0: → cd EFI\Tools → nuclear_settings.nsh
5. Type 'reset' to reboot
6. Verify via Redfish: GET /redfish/v1/Systems/Self/Bios
```

**Settings NOT in IFR (require manual BIOS entry):**
- tREFI = 65535 (no numeric setting found, must use BIOS UI)
- Curve Optimizer per-core offsets (ASUS-specific menu)
- PBO Scalar (ASUS-specific menu)

**Linux Monitoring Alternative** (Future):
- ASUS EC Sensors driver merged in kernel 6.18+ (`asus-ec-sensors`)
- Server currently on 6.8.0 - would need kernel upgrade
- Enables native `hwmon` access to fans/temps without BMC

---

## Phase 5: OS-Level Optimization

### 5.1 CPU Governor and Scheduling

```bash
ssh omni@100.94.47.77 << 'EOF'
# Set performance governor on all cores
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu
done

# Verify
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Disable CPU frequency scaling limits
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq; do
    cat ${cpu/min/max} | sudo tee $cpu
done

# Set NUMA balancing for inference workloads
echo 1 | sudo tee /proc/sys/kernel/numa_balancing

# Disable transparent huge pages (can cause latency spikes)
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
EOF
```

### 5.2 GPU Persistence and Clocks Script

```bash
# /usr/local/bin/gpu_extreme_oc.sh
#!/bin/bash
set -e

echo "Applying extreme GPU overclocks..."

# PRO 6000 (GPU 0) - Air cooled, conservative
nvidia-smi -i 0 -pm 1
nvidia-smi -i 0 -pl 600
nvidia-smi -i 0 -lgc 2100,2550

# RTX 5090 (GPU 1) - Liquid chilled NUCLEAR (13°C)
nvidia-smi -i 1 -pm 1
nvidia-smi -i 1 -pl 750
nvidia-smi -i 1 -lgc 2500,3150

# Lock memory clocks high for consistency
nvidia-smi -i 0 -lmc 2250,2250
nvidia-smi -i 1 -lmc 2200,2200

echo "GPU overclocks applied successfully"
nvidia-smi --query-gpu=index,name,power.limit,clocks.current.graphics,clocks.current.memory --format=csv
```

### 5.3 Systemd Service for Boot Persistence

Create the AI-optimized GPU overclock script (inlines all settings for single-file deployment):

```bash
# Create the script
sudo tee /usr/local/bin/gpu_ai_overclock.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "Applying AI-optimized GPU settings..."

# Cold bug safety check for RTX 5090 (crashes below -10°C)
GPU1_TEMP=$(nvidia-smi -i 1 --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
if [[ "$GPU1_TEMP" != "N/A" ]] && [[ "$GPU1_TEMP" -lt 0 ]]; then
    echo "ERROR: GPU 1 temp too low (${GPU1_TEMP}°C). Risk of cold bug crash."
    echo "Check chiller setpoint - RTX 5090 crashes below -10°C."
    exit 1
fi
echo "RTX 5090 temp: ${GPU1_TEMP}°C (safe)"

# PRO 6000 (GPU 0) - Air cooled
nvidia-smi -i 0 -pm 1
nvidia-smi -i 0 -c EXCLUSIVE_PROCESS
nvidia-smi -i 0 -pl 600
nvidia-smi -i 0 -lgc 2100,2550
nvidia-smi -i 0 --auto-boost-default=DISABLED 2>/dev/null || true

# RTX 5090 (GPU 1) - Liquid chilled NUCLEAR
nvidia-smi -i 1 -pm 1
nvidia-smi -i 1 -c EXCLUSIVE_PROCESS
nvidia-smi -i 1 -pl 750
nvidia-smi -i 1 -lgc 2500,3150
nvidia-smi -i 1 -lmc 2200,2200  # Lock memory high for AI bandwidth
nvidia-smi -i 1 --auto-boost-default=DISABLED 2>/dev/null || true

echo "AI GPU overclocks applied"
nvidia-smi --query-gpu=index,name,power.limit,clocks.current.graphics,clocks.current.memory --format=csv
SCRIPT

# Make executable
sudo chmod +x /usr/local/bin/gpu_ai_overclock.sh
```

Then the systemd service:

```bash
# /etc/systemd/system/gpu-overclock.service
[Unit]
Description=Apply AI-Optimized GPU Overclocks
After=nvidia-persistenced.service
Requires=nvidia-persistenced.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/gpu_ai_overclock.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gpu-overclock.service
```

---

## Phase 6: Inference Optimization (AI THROUGHPUT MAXIMUM)

### 6.0 llama.cpp Parameters Philosophy for AI Throughput

| Parameter | Low Throughput Setting | **High Throughput Setting** |
|-----------|------------------------|----------------------------|
| `--batch-size` | 512 | **4096** |
| `--ubatch-size` | 256 | **1024** |
| `--parallel` | 1 | **4-8** |
| `--tensor-split` | VRAM ratio | **Bandwidth ratio (65,35)** |
| `--flash-attn` | Optional | **REQUIRED** |
| `--cache-type-k` | f16 | **q4_1** (saves VRAM for more layers) |

**Key Insight**: For DeepSeek-R1 MoE, batch processing amortizes expert routing overhead.

### 6.1 Updated llama.cpp Launch Parameters (AI NUCLEAR)

```bash
#!/bin/bash
# /usr/local/bin/start_llama_ai_nuclear.sh
# Optimized for maximum AI inference throughput

LLAMA_SERVER=/path/to/llama-server
MODEL=/nvme/models/deepseek-r1-0528-q4km/DeepSeek-R1-0528-Q4_K_M.gguf

$LLAMA_SERVER \
    --model $MODEL \
    --host 0.0.0.0 \
    --port 8000 \
    --n-gpu-layers 19 \
    --tensor-split 65,35 \
    --ctx-size 8192 \
    --parallel 4 \
    --batch-size 4096 \
    --ubatch-size 1024 \
    --flash-attn \
    --cache-type-k q4_1 \
    --cache-type-v q4_1 \
    --threads 96 \
    --threads-batch 192 \
    --numa numactl \
    --mlock \
    --no-mmap \
    --cont-batching \
    --metrics
```

**Parameter Rationale:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `--tensor-split 65,35` | Bandwidth-weighted | 5090 has 60% higher bandwidth/GB |
| `--batch-size 4096` | Maximum | Amortizes MoE expert routing |
| `--ubatch-size 1024` | Large | Better GPU utilization |
| `--cache-type-k/v q4_1` | Quantized | More VRAM for layers |
| `--no-mmap` | Direct load | Avoid page fault overhead |
| `--cont-batching` | Enabled | Better multi-request handling |
| `--metrics` | Enabled | Prometheus endpoint for monitoring |

### 6.2 Environment Variables (AI Optimized)

```bash
# Add to /etc/environment or container env

# GPU Configuration
CUDA_VISIBLE_DEVICES=0,1
CUDA_DEVICE_ORDER=PCI_BUS_ID

# GGML Specific
GGML_CUDA_SPLIT_MODE=layer
GGML_CUDA_NO_PINNED=0
GGML_CUDA_FORCE_MMQ=0
GGML_CUDA_F16=1

# OpenMP for CPU threads
OMP_NUM_THREADS=192
OMP_PROC_BIND=spread
OMP_PLACES=cores
GOMP_CPU_AFFINITY="0-191"

# Disable GPU power management (handled by nvidia-smi)
CUDA_AUTO_BOOST=0

# Memory optimization
MALLOC_CONF=background_thread:true,dirty_decay_ms:0,muzzy_decay_ms:0
```

### 6.3 NUMA Verification (CRITICAL)

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== NUMA Configuration Check ==="
numactl --hardware

echo ""
echo "EXPECTED: 'available: 1 nodes' (NPS1 mode)"
echo "If shows multiple nodes, BIOS NPS setting is wrong!"

echo ""
echo "=== GPU NUMA Affinity ==="
nvidia-smi topo -m

echo ""
echo "=== Memory Latency Test ==="
numactl --membind=0 --cpunodebind=0 -- dd if=/dev/zero of=/dev/null bs=1M count=10000 2>&1 | tail -1
EOF
```

---

## Phase 7: Stress Testing Protocol

**COMPREHENSIVE SCRIPT**: For production stress testing, use `scripts/stress_test_extreme.sh` which includes:
- Combined CPU/GPU/Memory stress with 30-minute duration
- Real-time monitoring (turbostat, nvidia-smi dmon, dmesg)
- WHEA/MCE/ECC error detection with automatic abort on critical errors
- Progress reporting with temperatures and power draw
- Detailed results summary with pass/fail verdict

```bash
# Run the comprehensive stress test
ssh omni@100.94.47.77 "chmod +x ~/scripts/stress_test_extreme.sh && ~/scripts/stress_test_extreme.sh 1800"
```

Below are the individual test components for reference:

### 7.1 CPU Stress Test (30 minutes)

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== CPU Stress Test - 30 minutes ==="
# Monitor in background
turbostat --interval 5 -o /tmp/turbostat.log &
TURBO_PID=$!

# Heavy CPU load with memory pressure
stress-ng --cpu 192 --cpu-method matrixprod \
          --vm 8 --vm-bytes 32G \
          --timeout 1800s

kill $TURBO_PID 2>/dev/null

echo "=== Turbostat Summary ==="
tail -20 /tmp/turbostat.log
EOF
```

### 7.2 GPU Stress Test (30 minutes)

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== GPU Stress Test - 30 minutes ==="
# Use PyTorch or cuda-memtest

python3 << 'PYTHON'
import torch
import time

def gpu_burn(device_id, duration_seconds=1800):
    device = torch.device(f'cuda:{device_id}')
    print(f"Burning GPU {device_id} for {duration_seconds}s")
    
    # Allocate large tensors
    size = 16384
    a = torch.randn(size, size, device=device, dtype=torch.float16)
    b = torch.randn(size, size, device=device, dtype=torch.float16)
    
    start = time.time()
    iterations = 0
    while time.time() - start < duration_seconds:
        c = torch.matmul(a, b)
        iterations += 1
        if iterations % 100 == 0:
            print(f"GPU {device_id}: {iterations} iterations, {time.time()-start:.0f}s elapsed")
    
    print(f"GPU {device_id}: Completed {iterations} iterations")

import threading
t0 = threading.Thread(target=gpu_burn, args=(0, 1800))
t1 = threading.Thread(target=gpu_burn, args=(1, 1800))
t0.start()
t1.start()
t0.join()
t1.join()
PYTHON
EOF
```

### 7.3 Combined Stress + Error Monitoring

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== Starting Combined Stress Test with Error Monitoring ==="

# Background monitors
dmesg -w | grep -iE "mce|whea|error|ecc|corrected|uncorrected" > /tmp/errors.log &
DMESG_PID=$!

nvidia-smi dmon -s pucvmet -d 5 -o T > /tmp/gpu_monitor.log &
NVMON_PID=$!

# Run stress tests
timeout 1800s stress-ng --cpu 192 --vm 4 --vm-bytes 16G &
STRESS_PID=$!

# Wait and cleanup
wait $STRESS_PID
kill $DMESG_PID $NVMON_PID 2>/dev/null

echo "=== Error Log ==="
cat /tmp/errors.log
echo "=== GPU Monitor Summary ==="
tail -50 /tmp/gpu_monitor.log
EOF
```

### 7.4 Memory Stability Test

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== Memory Stress Test (ECC should catch errors) ==="
# Using memtester for targeted validation
sudo memtester 64G 2

# Check for ECC corrections
echo "=== ECC Status ==="
edac-util -s 2>/dev/null || echo "EDAC not available, check dmesg for ECC events"
dmesg | grep -iE "ecc|edac|ce:|ue:" | tail -20
EOF
```

---

## Phase 8: AI Inference Benchmark Suite

### 8.1 llama-bench Validation (AI OPTIMIZED)

```bash
ssh omni@100.94.47.77 << 'EOF'
cd /path/to/llama.cpp/build/bin

echo "=== AI-Optimized Benchmark: DeepSeek-R1-0528 Q4_K_M ==="
echo "Using AI-optimized settings: tensor-split 65,35, batch 4096"

# Run benchmarks with multiple prompt/generation lengths
for PROMPT_LEN in 512 1024 2048; do
    for GEN_LEN in 128 256 512; do
        echo "Testing p=$PROMPT_LEN n=$GEN_LEN"
        ./llama-bench \
            -m /nvme/models/deepseek-r1-0528-q4km/DeepSeek-R1-0528-Q4_K_M.gguf \
            -p $PROMPT_LEN \
            -n $GEN_LEN \
            -ngl 19 \
            -ts 65,35 \
            -fa \
            -b 4096 \
            -ub 1024 \
            -t 96 \
            --cache-type-k q4_1 \
            -r 3
    done
done

echo ""
echo "=== Batch Size Impact Test ==="
for BATCH in 512 1024 2048 4096; do
    echo "Testing batch size: $BATCH"
    ./llama-bench \
        -m /nvme/models/deepseek-r1-0528-q4km/DeepSeek-R1-0528-Q4_K_M.gguf \
        -p 512 -n 128 \
        -ngl 19 -ts 65,35 -fa -b $BATCH -t 96 \
        --cache-type-k q4_1 \
        -r 1
done
EOF
```

### 8.2 Real-World AI Inference Test

**NOTE**: The production container `deepseek-r1-0528` runs with `--network host`, so localhost:8000 is accessible from both host and container. If using bridge networking, add `-p 8000:8000` to docker run.

```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== Real-World Inference Test ==="
# This tests actual throughput with realistic prompts
# Assumes production server already running at port 8000

# Verify server is healthy
curl -s http://localhost:8000/health || { echo "Server not running"; exit 1; }

# Run concurrent requests (simulates real AI workload)
echo "Sending 4 concurrent requests..."
for i in 1 2 3 4; do
    (
        START=$(date +%s%N)
        curl -s http://localhost:8000/v1/completions \
            -H "Content-Type: application/json" \
            -d '{
                "prompt": "Explain the theory of relativity in simple terms:",
                "max_tokens": 256,
                "temperature": 0.7
            }' > /dev/null
        END=$(date +%s%N)
        DURATION=$(( (END - START) / 1000000 ))
        echo "Request $i completed in ${DURATION}ms"
    ) &
done
wait

echo ""
echo "=== Server Metrics ==="
curl -s http://localhost:8000/metrics | grep -E "tokens|requests"
EOF
```

### 8.3 Expected Performance Targets (AI NUCLEAR)

| Metric | Baseline | **AI NUCLEAR Target** | Improvement |
|--------|----------|----------------------|-------------|
| Generation | 11.35 tok/s | **13.5-14.5 tok/s** | +19-28% |
| Prompt Eval | 23.14 tok/s | **28-32 tok/s** | +21-38% |
| P95 Latency | ~85ms | **<65ms** | -24% |
| Memory BW Util | ~70% | **>85%** | +15% |
| GPU Util | ~75% | **>90%** | +15% |

**AI Optimization Gains Breakdown:**

| Optimization | Expected Gain |
|--------------|---------------|
| DF C-States Disabled | +3-5% |
| FCLK 2100 MHz | +2-3% |
| tREFI 65535 | +5-8% |
| IOMMU Disabled (P2P) | +2-3% |
| Tensor Split 65,35 | +3-5% |
| Batch 4096 | +2-4% |
| Memory Clock +2000 | +3-5% |
| **Combined** | **+15-25%** |

**Reality Check**: With all AI optimizations applied, **13.5-14.5 tok/s** is achievable. The 20 tok/s benchmark requires symmetric 2x PRO 6000 Blackwell (hardware upgrade path).

---

## Phase 9: Rollback Procedures

### 9.1 If System Fails to Boot

1. Clear CMOS via motherboard jumper or button
2. Remove battery for 30 seconds
3. Boot with default BIOS settings
4. Re-apply settings incrementally

### 9.2 If Inference Performance Degrades

```bash
# Restore conservative settings
nvidia-smi -i 0 -rgc  # Reset GPU 0 clocks
nvidia-smi -i 1 -rgc  # Reset GPU 1 clocks
nvidia-smi -i 0 -pl 600
nvidia-smi -i 1 -pl 575  # Stock power limit

# Restart llama-server with baseline config
docker restart deepseek-r1-0528
```

### 9.3 If Memory Errors Occur

1. Loosen primary timings first: tCL/tRCD/tRP from 34 to 36
2. If still failing, try tCL/tRCD/tRP at 38
3. tREFI 65535 is proven stable - unlikely to be the cause
4. Check DIMM temperatures - if above 35°C, investigate airflow
5. If persistent errors, run `memtester` overnight with stock timings

---

## Definition of Done

### MANDATORY Checks

- [ ] System boots successfully after BIOS changes
- [ ] `numactl --hardware` shows `available: 1 nodes` (NPS1)
- [ ] CPU reaches **5.5+ GHz** all-core under load (verify with turbostat)
- [ ] CPU power draw hits **1400W** without throttle (verify with turbostat)
- [ ] GPU 0 (PRO 6000) runs at **2500+ MHz** sustained
- [ ] GPU 1 (RTX 5090) runs at **3100+ MHz** sustained, temps **<45°C**
- [ ] 30-minute stress test passes with **ZERO** WHEA/MCE errors
- [ ] ECC log shows **ZERO** uncorrectable errors
- [ ] `llama-bench` achieves **>13 tok/s** generation

### Performance Verification

```bash
# Final validation command
ssh omni@100.94.47.77 << 'EOF'
echo "=== FINAL PERFORMANCE CHECK ==="
echo "CPU Frequency (all cores):"
cat /proc/cpuinfo | grep MHz | sort -u | tail -1

echo "GPU Status:"
nvidia-smi --query-gpu=index,name,clocks.current.graphics,temperature.gpu,power.draw --format=csv

echo "Memory Bandwidth (quick test):"
cd /tmp/stream && OMP_NUM_THREADS=192 ./stream 2>/dev/null | grep -E "Copy:|Scale:|Add:|Triad:"

echo "Inference Benchmark:"
curl -s -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"deepseek-r1-0528","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' | jq '.usage'
EOF
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CPU thermal throttle | **Negligible** (13°C chiller) | Performance drop | Monitor turbostat |
| GPU cold bug crash | **Negligible** (13°C > 5°C) | System hang | Already safe |
| Memory data corruption | **Low** (ECC + USER PROVEN tREFI) | Data loss | 65535 validated |
| PSU overload | **Medium** | System shutdown | ~2800W peak (1400+750+600+50), need **3000W PSU** |
| Silicon degradation | Medium (long-term) | Shortened lifespan | Accept for performance |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2026-01-29 | **NUCLEAR**: 1400W CPU, 750W GPU, tREFI 65535, CL34 timings based on user-proven 13°C chiller setup |
| 2.0 | 2026-01-29 | Initial EXTREME version with liquid chiller optimizations |

---

*Document prepared by Fahad, The Executive Architect. This is NUCLEAR territory - execute only with proper PSU capacity (3000W+).*
