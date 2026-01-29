# Performance Tuning Plan: Operation Ultrathink

## 1. Hardware Baseline Restoration (In Progress)
- **Topology**: NPS1 (Unified NUMA) for 671B inference.
- **PCIe**: Above 4G Decoding + Re-size BAR (Essential for 96GB + 32GB VRAM mapping).
- **Security**: Secure Boot Disabled (via MOK bypass if BIOS toggle fails).
- **CPU**: PBO Enabled (removing TDP limits).

## 2. Memory Optimization (PMIC Lock Workaround)
- **Issue**: Hynix A-die locked to 1.435V.
- **Strategy**: 
    1. Check BIOS for `Enable Platform PMIC Control` to bypass lock.
    2. If locked, focus on **Tightening Timings** at 1.1V/1.25V.
    3. Target: `tRFC` reduction (huge impact on AI), `tREFI` increase.

## 3. GPU Tuning
- **RTX 6000 Ada**: 
    - Power Limit: Likely locked. Check `nvidia-smi -q -d POWER`.
    - Clock: Curve optimization to sustain higher boost at stock power.
- **RTX 5090**: 
    - Undervolt for efficiency (0.95V @ 2700MHz?) to reduce heat dump into chassis, aiding the 6000 Ada.

## 4. Stress Testing Suite
- **Script**: `scripts/stress_test_ai.sh`
- **Components**:
    - `llama-bench`: Inference stability.
    - `stress-ng`: CPU/RAM stability.
    - `gpu-burn` / PyTorch GEMM: GPU thermal saturation.
