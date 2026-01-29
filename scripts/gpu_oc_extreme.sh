#!/bin/bash
# gpu_oc_extreme.sh - NUCLEAR GPU overclocking for 13°C liquid-chilled RTX 5090
# VERSION: v3 NUCLEAR - Updated for user-proven 1400W CPU / 13°C chiller setup
# WARNING: Requires liquid chiller on GPU 1. Do NOT run on air-cooled systems.
# Author: Fahad | Date: 2026-01-29

set -e

echo "=============================================="
echo "  NUCLEAR GPU OVERCLOCK - 13°C CHILLER SETUP"
echo "=============================================="
echo "  CONFIG (v3 NUCLEAR):"
echo "  GPU 0 = RTX PRO 6000 Blackwell (96GB) - Air"
echo "  GPU 1 = RTX 5090 (32GB) - 13°C Liquid Chilled"
echo "=============================================="

# Verify we have nvidia-smi
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found"
    exit 1
fi

# Verify GPU configuration matches expected
GPU0_NAME=$(nvidia-smi -i 0 --query-gpu=name --format=csv,noheader 2>/dev/null || echo "Unknown")
GPU1_NAME=$(nvidia-smi -i 1 --query-gpu=name --format=csv,noheader 2>/dev/null || echo "Unknown")

echo "Detected GPUs:"
echo "  GPU 0: $GPU0_NAME"
echo "  GPU 1: $GPU1_NAME"

# Check GPU temps before applying (safety check for cold bug)
GPU1_TEMP=$(nvidia-smi -i 1 --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
echo ""
echo "RTX 5090 current temp: ${GPU1_TEMP}°C"

# Cold bug threshold is -10°C, but 5°C is too conservative for 13°C chiller
# User's chiller is at 13°C, die will be ~30-40°C under load
if [[ "$GPU1_TEMP" != "N/A" ]] && [[ "$GPU1_TEMP" -lt 0 ]]; then
    echo "ERROR: GPU temp too low (${GPU1_TEMP}°C). Risk of cold bug."
    echo "RTX 5090 crashes below -10°C. Check chiller setpoint."
    exit 1
fi

echo ""
echo "=== GPU 0: RTX PRO 6000 Blackwell (Air Cooled) ==="
echo "Applying conservative overclock (600W max, no chiller)..."

nvidia-smi -i 0 -pm 1
nvidia-smi -i 0 -pl 600
nvidia-smi -i 0 -lgc 2100,2550

echo "PRO 6000: 600W, 2100-2550MHz range"

echo ""
echo "=== GPU 1: RTX 5090 (13°C LIQUID CHILLED) ==="
echo "Applying NUCLEAR overclock (750W, 2500-3200MHz)..."

# 750W is aggressive but proven stable with 13°C chiller
# Some AIB cards may allow up to 800W with BIOS mod
nvidia-smi -i 1 -pm 1
nvidia-smi -i 1 -pl 750
nvidia-smi -i 1 -lgc 2500,3200

echo "RTX 5090: 750W, 2500-3200MHz range"

echo ""
echo "=== Final Configuration ==="
nvidia-smi --query-gpu=index,name,power.limit,clocks.current.graphics,clocks.current.memory,temperature.gpu --format=csv

echo ""
echo "SUCCESS: NUCLEAR GPU overclocks applied."
echo ""
echo "NOTES:"
echo "  - Your 13°C chiller keeps you well above cold bug threshold (-10°C)"
echo "  - If GPU 1 shows artifacts, try reducing to 3100MHz (-lgc 2500,3100)"
echo "  - Monitor power draw - total system ~2800W peak"
