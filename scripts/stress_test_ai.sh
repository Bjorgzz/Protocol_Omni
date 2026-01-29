#!/bin/bash
# stress_test_ai.sh
# Runs stress-ng and checks GPU

echo "=== System Info ==="
uptime
nvidia-smi -L
numactl --hardware

echo "=== Starting CPU/RAM Stress (60s) ==="
stress-ng --cpu 32 --vm 2 --vm-bytes 16G --timeout 60s

echo "=== Done ==="
