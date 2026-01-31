# Memory Bandwidth Optimization: DDR5-6400 MT/s Configuration Guide

**Date**: 2026-01-30  
**Platform**: ASUS Pro WS WRX90E-SAGE SE + AMD TR PRO 9995WX  
**Memory**: 8x SK Hynix HMCGY4MHBRB489N 48GB RDIMM (384GB total)  
**Current**: 6000 MT/s | **Target**: 6400 MT/s (+6.67% bandwidth)  
**Risk Level**: LOW (within manufacturer spec)

---

## Executive Summary

Your SK Hynix HMCGY4MHBRB489N modules are **rated for 6400 MT/s** at 1.1V but currently running at 6000 MT/s (BIOS conservative default). This guide enables full rated speed plus tREFI optimization for maximum AI inference bandwidth.

**Expected Gains**:
| Configuration | Bandwidth | Gain |
|---------------|-----------|------|
| Current (6000 MT/s + tREFI default) | ~200-210 GB/s | Baseline |
| Current (6000 MT/s + tREFI=65535) | ~236 GB/s | +15% (verified S-020) |
| **Target (6400 MT/s + tREFI=65535)** | **~280-300 GB/s** | **+25-30%** |

---

## Pre-Flight Checklist

### Current Known-Good Settings (KEEP THESE)
- [x] Gear Down Mode: **Disabled** ✅
- [x] Power Down Mode: **Disabled** ✅  
- [x] Context Restore: **Disabled** ✅
- [x] Nitro Settings: **1-3-1** ✅
- [x] DF C-States: **Disabled** (Redfish verified)
- [x] APBDIS: **1** (Redfish verified)
- [x] Global C-States: **Disabled** (Redfish verified)
- [x] NPS: **NPS1** (Redfish verified)

### Pre-Change Verification (Run Before BIOS Changes)
```bash
# SSH to server and capture baseline
ssh omni@100.94.47.77 << 'EOF'
echo "=== BASELINE CAPTURE $(date) ==="
echo "--- Memory Speed ---"
sudo dmidecode -t memory | grep "Configured Memory Speed" | head -1
echo "--- STREAM Benchmark ---"
cd /tmp && curl -sO https://www.cs.virginia.edu/stream/FTP/Code/stream.c
gcc -O3 -fopenmp -DSTREAM_ARRAY_SIZE=100000000 -DNTIMES=10 stream.c -o stream
OMP_NUM_THREADS=192 ./stream | grep -E "Triad|Copy"
echo "--- Current tREFI (Redfish) ---"
curl -sk -u admin:PASSWORD https://192.168.3.202/redfish/v1/Systems/Self/Bios | jq -r '.Attributes.CbsCmnMemDramRefreshRateSHP'
EOF
```

---

## BIOS Configuration Steps

### Step 1: Enter BIOS AI Tweaker
1. Reboot system (via BMC KVM or `sudo reboot`)
2. Press **F2** during POST to enter BIOS
3. Navigate: **Ai Tweaker** tab (top menu)

### Step 2: Set Memory Frequency to 6400 MT/s

**Navigation**: `Ai Tweaker` → `Ai Overclock Tuner`

| Setting | Current | Target | Notes |
|---------|---------|--------|-------|
| **Ai Overclock Tuner** | Auto | **Manual** | Enables frequency override |
| **Memory Frequency** | Auto (6000) | **DDR5-6400** | Select from dropdown |

**Alternative Method** (if no EXPO profile):
1. Set `Ai Overclock Tuner` → **Manual**
2. Find `DRAM Frequency` or `Memory Frequency Multiplier`
3. Select **6400** (or closest: 6400/6333/6466)

**SK Hynix HMCGY4MHBRB489N Compatibility**:
- Rated: 6400 MT/s @ 1.1V (PMIC-locked voltage)
- No EXPO profile (RDIMM, not consumer UDIMM)
- Timings: Should auto-train to CL48-50 at 6400 MT/s

### Step 3: Verify/Set tREFI = 65535

**Navigation**: `Ai Tweaker` → `DRAM Timing Control` → (scroll down or `Advanced`)

| Setting | Location | Value | Impact |
|---------|----------|-------|--------|
| **tREFI** | DRAM Timing → Advanced/Tertiary | **65535** | +15-20% bandwidth |
| **tRFC1** | DRAM Timing → Secondary | **312** (keep) | Already optimal |
| **tRFC2** | DRAM Timing → Secondary | **192** (keep) | Already optimal |

**If tREFI field not visible**:
- Look under: `AMD CBS` → `UMC Common Options` → `DDR Timing Configuration`
- Alternative name: `DRAM Refresh Interval`

### Step 4: Confirm Stability Settings

These should already be set, but verify:

| Setting | Location | Required Value | Why |
|---------|----------|----------------|-----|
| **Gear Down Mode** | DRAM Timing | **Disabled** | Latency reduction (RDIMM handles stability) |
| **Power Down Enable** | DRAM Timing | **Disabled** | Prevents idle clock gating |
| **Context Restore** | DRAM Timing | **Disabled** | Forces clean training each boot |
| **Command Rate** | DRAM Timing | **1T** or **Auto** | 1T if stable, else Auto |

### Step 5: Secondary Timings (Optional Tightening)

SK Hynix A/M-die tolerates aggressive timings. If POST fails at 6400 MT/s, try loosening:

| Timing | Conservative | Aggressive | Fallback |
|--------|--------------|------------|----------|
| **tCL** | 48 | 46 | 50 |
| **tRCD** | 48 | 46 | 50 |
| **tRP** | 48 | 46 | 50 |
| **tRAS** | 96 | 92 | 100 |
| **tRFC1** | 312 | 295 | 350 |

**Current timings (22-8-8-39)** are at 6000 MT/s. At 6400 MT/s, expect auto-training to ~46-48-48-96.

### Step 6: Save and Exit

1. Press **F10** to save
2. Confirm save and reboot
3. **Watch POST carefully** for Q-code errors

---

## POST Troubleshooting

### If System Fails to POST (Q-Code: 0d, 55, or memory error)

**Automatic Recovery**: ASUS will auto-retry with safe settings after 3 failed POST attempts.

**Manual Recovery**:
1. Power off completely (hold power 10s)
2. Clear CMOS: Use motherboard jumper or remove battery 30s
3. Re-enter BIOS with defaults
4. Apply settings incrementally:
   - First: 6400 MT/s only (leave timings Auto)
   - If stable: Add tREFI=65535
   - If stable: Tighten timings

### Common Q-Codes and Solutions

| Q-Code | Meaning | Solution |
|--------|---------|----------|
| **0d** | Memory training fail | Loosen timings or drop to 6200 MT/s |
| **55** | Memory not detected | Reseat DIMMs, check slot population |
| **b2** | Legacy boot issue | Unrelated to memory |
| **00** | Successful POST | Continue to OS |

### If POST Succeeds but Unstable in OS

Run memory stress test:
```bash
# Quick validation (5 minutes)
ssh omni@100.94.47.77 "sudo apt-get install -y stressapptest && stressapptest -W -s 300"

# Extended validation (30 minutes)  
ssh omni@100.94.47.77 "stressapptest -W -s 1800 --pause_delay 300"
```

If errors occur:
1. Increase tRFC1 by +32 (e.g., 312 → 344)
2. Or reduce tREFI to 50000 (if DIMM temps >45°C)

---

## Post-Change Verification

### Immediate Verification (After Successful POST)
```bash
ssh omni@100.94.47.77 << 'EOF'
echo "=== POST-CHANGE VERIFICATION $(date) ==="

echo "--- Memory Speed (MUST show 6400) ---"
sudo dmidecode -t memory | grep "Configured Memory Speed" | head -1

echo "--- DIMM Temperature (should be <45C) ---"
ipmitool sensor list | grep -i dimm | head -4

echo "--- STREAM Benchmark (Target: >270 GB/s Triad) ---"
cd /tmp
OMP_NUM_THREADS=192 ./stream | grep -E "Triad|Copy"
EOF
```

### Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Memory Speed** | 6000 MT/s | **6400 MT/s** | +6.67% |
| **STREAM Triad** | 236 GB/s | **280-300 GB/s** | +18-27% |
| **STREAM Copy** | ~220 GB/s | **260-280 GB/s** | +18-27% |

### LLM Inference Benchmark
```bash
# After memory change, benchmark DeepSeek-R1
curl -s http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"Explain quantum computing in 100 words"}],"max_tokens":200}' | jq '.usage'
```

**Expected**: 10.4 → **12-14 tok/s** (+15-35% from bandwidth gain)

---

## Rollback Procedure

If system becomes unstable after 6400 MT/s:

### Quick Rollback (Via BIOS)
1. Enter BIOS (F2 during POST)
2. `Ai Tweaker` → `Ai Overclock Tuner` → **Auto**
3. F10 save and exit
4. System returns to 6000 MT/s safe defaults

### Emergency Rollback (If No POST)
1. Power off completely
2. Clear CMOS (jumper or battery removal)
3. Boot with defaults
4. Manually re-apply previous 6000 MT/s + tREFI=65535 config

---

## Summary: Exact Changes Required

| Step | Setting | From | To |
|------|---------|------|-----|
| 1 | Ai Overclock Tuner | Auto | **Manual** |
| 2 | Memory Frequency | 6000 | **6400** |
| 3 | tREFI (verify) | Default/3.9us | **65535** |
| 4 | (Keep) Gear Down | Disabled | Disabled |
| 5 | (Keep) Power Down | Disabled | Disabled |
| 6 | (Keep) Context Restore | Disabled | Disabled |

**Total BIOS time**: ~2-3 minutes  
**Risk**: LOW (within spec, reversible)  
**Reward**: +25-35% memory bandwidth → +15-35% LLM inference throughput

---

## References

- SK Hynix HMCGY4MHBRB489N Datasheet: 6400 MT/s @ 1.1V rated
- ASUS WRX90E-SAGE BIOS Manual: E22761
- S-020 Benchmark: 236.4 GB/s @ 6000 MT/s + tREFI=65535
- AMD DDR5 Tuning Guide: tREFI = "most impactful after primaries"

---

*Document created: 2026-01-30 | Protocol OMNI Operation Velocity v4*
