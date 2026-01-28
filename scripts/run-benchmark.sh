#!/bin/bash
set -euo pipefail

BENCHMARK_DIR="${HOME}/benchmarks/$(date +%Y-%m-%d)-benchmark"
RESULTS_FILE="benchmark-results.txt"
SERVER_URL="${LLAMA_SERVER_URL:-http://localhost:8000}"

mkdir -p "$BENCHMARK_DIR"
OUTPUT="$BENCHMARK_DIR/$RESULTS_FILE"

echo "=== Benchmark $(date) ===" | tee "$OUTPUT"
echo "Server: $SERVER_URL" | tee -a "$OUTPUT"
echo "" | tee -a "$OUTPUT"

echo "=== System State ===" | tee -a "$OUTPUT"

if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
  echo "CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)" | tee -a "$OUTPUT"
else
  echo "CPU Governor: N/A (cpufreq not available)" | tee -a "$OUTPUT"
fi

if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=name,clocks.current.graphics,temperature.gpu,power.draw --format=csv | tee -a "$OUTPUT"
else
  echo "GPU: N/A (nvidia-smi not available)" | tee -a "$OUTPUT"
fi
echo "" | tee -a "$OUTPUT"

echo "=== Short Prompt Benchmark ===" | tee -a "$OUTPUT"
curl -s "$SERVER_URL/completion" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write a haiku about AI:","n_predict":64,"temperature":0.7}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d.get('timings', {})
print(f'Prompt:     {t.get(\"prompt_n\",0)} tokens @ {t.get(\"prompt_per_second\",0):.2f} tok/s')
print(f'Generation: {t.get(\"predicted_n\",0)} tokens @ {t.get(\"predicted_per_second\",0):.2f} tok/s')
" | tee -a "$OUTPUT"

echo "" | tee -a "$OUTPUT"
echo "=== Long Prompt Benchmark ===" | tee -a "$OUTPUT"

LONG_PROMPT="Provide a comprehensive analysis of transformer architecture optimizations including attention mechanisms, KV cache strategies, quantization techniques, and memory bandwidth considerations for inference at scale."

curl -s "$SERVER_URL/completion" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"$LONG_PROMPT\",\"n_predict\":128,\"temperature\":0.7}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d.get('timings', {})
print(f'Prompt:     {t.get(\"prompt_n\",0)} tokens @ {t.get(\"prompt_per_second\",0):.2f} tok/s')
print(f'Generation: {t.get(\"predicted_n\",0)} tokens @ {t.get(\"predicted_per_second\",0):.2f} tok/s')
" | tee -a "$OUTPUT"

echo "" | tee -a "$OUTPUT"
echo "Results saved to: $OUTPUT"
