#!/bin/bash
# stress_test_extreme.sh - Combined CPU/GPU/Memory stress test with monitoring
# CORRECTED VERSION: Proper error handling, longer duration, comprehensive logging
# Run for 30 minutes to validate extreme overclock stability
# Author: Fahad | Date: 2026-01-29

set -e

DURATION=${1:-1800}  # Default 30 minutes (1800 seconds)
LOG_DIR="/tmp/stress_test_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$LOG_DIR"

echo "=============================================="
echo "  EXTREME STRESS TEST - ${DURATION}s"
echo "  Logs: $LOG_DIR"
echo "=============================================="

cleanup() {
    echo ""
    echo "Cleaning up background processes..."
    pkill -f "stress-ng" 2>/dev/null || true
    kill $TURBO_PID $NVMON_PID $DMESG_PID $GPU_PID 2>/dev/null || true
}

trap cleanup EXIT

# Verify system state before starting
echo ""
echo "=== Pre-Flight Checks ==="
echo "CPU governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'unknown')"
echo "NUMA nodes: $(numactl --hardware 2>/dev/null | head -1 || echo 'unknown')"
nvidia-smi --query-gpu=index,name,temperature.gpu,power.limit --format=csv

echo ""
echo "=== Starting Monitors ==="

# CPU monitoring (turbostat)
if command -v turbostat &> /dev/null; then
    echo "Starting turbostat..."
    turbostat --interval 10 -o "$LOG_DIR/turbostat.log" 2>&1 &
    TURBO_PID=$!
else
    echo "turbostat not available, using mpstat"
    mpstat -P ALL 10 > "$LOG_DIR/cpu_monitor.log" 2>&1 &
    TURBO_PID=$!
fi

# GPU monitoring
echo "Starting GPU monitor..."
nvidia-smi dmon -s pucvmet -d 5 -o T > "$LOG_DIR/gpu_monitor.log" 2>&1 &
NVMON_PID=$!

# Error monitoring
echo "Starting error monitor..."
dmesg -wT 2>/dev/null | grep -iE "mce|whea|error|ecc|corrected|uncorrected|nvme|xhci" > "$LOG_DIR/errors.log" 2>&1 &
DMESG_PID=$!

echo ""
echo "=== Starting Stress Test ==="

# CPU stress with memory pressure
echo "Starting CPU stress (192 threads, matrix multiply + memory)..."
stress-ng --cpu 192 --cpu-method matrixprod \
          --vm 8 --vm-bytes 32G \
          --timeout ${DURATION}s \
          --metrics-brief \
          2>&1 | tee "$LOG_DIR/stress_ng.log" &
STRESS_PID=$!

# GPU stress
echo "Starting GPU stress (both GPUs, FP16 GEMM)..."
python3 - $DURATION << 'PYTHON' 2>&1 | tee "$LOG_DIR/gpu_stress.log" &
import torch
import time
import sys

duration = int(sys.argv[1]) if len(sys.argv) > 1 else 1800

print(f"GPU stress test starting for {duration}s")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")

tensors = {}
for device_id in range(torch.cuda.device_count()):
    try:
        device = torch.device(f'cuda:{device_id}')
        name = torch.cuda.get_device_name(device_id)
        print(f"GPU {device_id}: {name}")
        size = 8192
        tensors[device_id] = {
            'a': torch.randn(size, size, device=device, dtype=torch.float16),
            'b': torch.randn(size, size, device=device, dtype=torch.float16)
        }
        print(f"GPU {device_id}: Tensors allocated ({size}x{size} FP16)")
    except Exception as e:
        print(f"GPU {device_id}: Setup failed - {e}")

start = time.time()
iterations = 0
errors = 0

while time.time() - start < duration:
    for device_id, t in tensors.items():
        try:
            c = torch.matmul(t['a'], t['b'])
            del c
            torch.cuda.synchronize(device_id)
        except Exception as e:
            errors += 1
            print(f"GPU {device_id} error: {e}")
    
    iterations += 1
    
    if iterations % 50 == 0:
        elapsed = time.time() - start
        remaining = duration - elapsed
        print(f"Progress: {iterations} iterations, {elapsed:.0f}s elapsed, {remaining:.0f}s remaining, {errors} errors")

print(f"\nGPU stress completed:")
print(f"  Total iterations: {iterations}")
print(f"  Total errors: {errors}")
print(f"  Status: {'PASSED' if errors == 0 else 'FAILED'}")
PYTHON
GPU_PID=$!

echo ""
echo "=== Stress Test Running ==="
echo "Duration: ${DURATION}s"
echo "Logs: $LOG_DIR"
echo "Press Ctrl+C to abort (will show partial results)"
echo ""

# Progress indicator
elapsed=0
while [ $elapsed -lt $DURATION ]; do
    sleep 60
    elapsed=$((elapsed + 60))
    pct=$((elapsed * 100 / DURATION))
    
    # Quick status
    cpu_freq=$(grep "cpu MHz" /proc/cpuinfo 2>/dev/null | head -1 | awk '{printf "%.0f", $4}' || echo "N/A")
    gpu0_temp=$(nvidia-smi -i 0 --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
    gpu1_temp=$(nvidia-smi -i 1 --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
    gpu0_pwr=$(nvidia-smi -i 0 --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
    gpu1_pwr=$(nvidia-smi -i 1 --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
    errors=$(wc -l < "$LOG_DIR/errors.log" 2>/dev/null || echo "0")
    
    printf "[%3d%%] CPU: %sMHz | GPU0: %s°C/%sW | GPU1: %s°C/%sW | Errors: %s\n" \
        "$pct" "$cpu_freq" "$gpu0_temp" "$gpu0_pwr" "$gpu1_temp" "$gpu1_pwr" "$errors"
    
    # Early exit if too many errors
    if [ "$errors" -gt 10 ]; then
        echo "ERROR: Too many errors detected, aborting stress test"
        break
    fi
done

echo ""
echo "=== Stress Test Complete ==="

# Wait for background processes
wait $STRESS_PID 2>/dev/null || true
wait $GPU_PID 2>/dev/null || true

echo ""
echo "=============================================="
echo "               RESULTS SUMMARY"
echo "=============================================="

echo ""
echo "--- System Errors (WHEA/MCE/ECC) ---"
if [ -s "$LOG_DIR/errors.log" ]; then
    error_count=$(wc -l < "$LOG_DIR/errors.log")
    echo "ERRORS DETECTED: $error_count"
    echo ""
    cat "$LOG_DIR/errors.log"
    RESULT="FAILED"
else
    echo "No critical errors detected."
    RESULT="PASSED"
fi

echo ""
echo "--- CPU Performance Summary ---"
if [ -f "$LOG_DIR/turbostat.log" ]; then
    echo "Last 10 turbostat readings:"
    tail -10 "$LOG_DIR/turbostat.log" | head -5
else
    echo "Turbostat data not available"
fi

echo ""
echo "--- GPU Performance Summary ---"
if [ -f "$LOG_DIR/gpu_monitor.log" ]; then
    echo "Peak GPU metrics:"
    echo "  GPU 0 max temp: $(awk 'NR>1 {print $3}' "$LOG_DIR/gpu_monitor.log" | sort -n | tail -1)°C"
    echo "  GPU 1 max temp: $(awk 'NR>1 {print $3}' "$LOG_DIR/gpu_monitor.log" | sort -n | tail -1)°C"
fi

echo ""
echo "--- GPU Stress Log ---"
if [ -f "$LOG_DIR/gpu_stress.log" ]; then
    tail -5 "$LOG_DIR/gpu_stress.log"
fi

echo ""
echo "=============================================="
echo "  STRESS TEST VERDICT: $RESULT"
echo "  Full logs: $LOG_DIR"
echo "=============================================="

if [ "$RESULT" = "FAILED" ]; then
    echo ""
    echo "Recommended actions:"
    echo "  1. Check $LOG_DIR/errors.log for specific error types"
    echo "  2. If WHEA errors: Reduce CPU overclock (CO offsets, PPT)"
    echo "  3. If GPU errors: Reduce clock targets (-lgc) or power (-pl)"
    echo "  4. If memory errors: Loosen tREFI, primary timings"
    exit 1
fi
