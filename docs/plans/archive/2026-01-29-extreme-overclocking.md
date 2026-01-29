# Extreme Overclocking Plan: Operation Velocity

**Objective**: Maximize DeepSeek-R1 inference performance via aggressive hardware tuning.

## 1. GPU Optimization (The 1400W Envelope)

### RTX 5090 (32GB)
- **Power Limit**: Target **800W** (Factory Max).
- **Core Clock**: Lock to **3000 MHz** (`nvidia-smi -lgc 3000`).
- **Memory**: +1000 MHz offset.
- **Cooling**: Liquid Chiller active. Target < 45°C under load.

### RTX 6000 Ada Blackwell (96GB)
- **Power Limit**: Target **600W** (Factory Max).
- **Core Clock**: Curve optimize for sustained **2800 MHz**.
- **Priority**: VRAM stability > Core clock (prevent ECC errors).

### Implementation Script (`scripts/gpu_oc_extreme.sh`)
```bash
#!/bin/bash
# Enable persistence
sudo nvidia-smi -pm 1

# Set Power Limits
sudo nvidia-smi -i 0 -pl 800  # 5090
sudo nvidia-smi -i 1 -pl 600  # 6000 Ada

# Lock Clocks (Prevent Jitter)
sudo nvidia-smi -i 0 -lgc 3000,3000
sudo nvidia-smi -i 1 -lgc 2800,2800
```

## 2. Memory Tuning (Hynix PMIC Bypass)

**Target**: Unlock >1.435V for 6400 MT/s CL30 stability.

### BIOS Navigation (ASUS WRX90)
1. **Ai Tweaker** (if visible) OR **Advanced -> AMD Overclocking**.
2. Look for **"Tweaker's Paradise"** or **"PMIC Voltages"**.
3. Setting: **"Enable Platform PMIC Control"** -> **Enabled**.
4. Setting: **"High Voltage Mode"** -> **Enabled**.

### Timing Targets (If Voltage Locked)
- **tRFC**: Reduce to **350ns** (approx 400-500 cycles @ 6000).
- **tREFI**: Increase to **65535** (Max refresh interval).
- **Performance Impact**: High `tREFI` + Low `tRFC` = +5-10% tok/s.

## 3. CPU PBO Optimization

- **Cooling**: Liquid Chiller active. Thermal headroom is massive.
- **PBO Scalar**: 10x.
- **Curve Optimizer**: **-20 to -30 All Core** (Aggressive undervolt possible with chiller).
- **Boost Override**: +200 MHz.
- **Thermal Throttle Limit**: Manual **95°C** (Safety).

## 4. Verification & Stress Test

### Suite: `scripts/stress_test_extreme.sh`
1. **GPU Burn**: 5 mins of heavy CUDA load.
2. **CPU AVX-512**: `stress-ng --matrix 0 --matrix-size 4096`.
3. **Inference**: `llama-bench` run for perplexity deviation check.

**Success Criteria**:
- No WHEA errors (`dmesg | grep WHEA`).
- No GPU throttling (`nvidia-smi -q -d PERFORMANCE`).
- Stable 12+ tok/s on DeepSeek-R1-0528.
