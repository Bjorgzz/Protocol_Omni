#!/bin/bash
# KTransformers Benchmark Script
# Compares KT+SGLang (port 8005) vs llama.cpp (port 8000)
#
# Usage: ./benchmark-kt.sh [num_requests]

set -e

NUM_REQUESTS=${1:-10}
PROMPT="Write a Python function to calculate Fibonacci numbers recursively with memoization. Include type hints and a docstring."

echo "=== KTransformers vs llama.cpp Benchmark ==="
echo "Prompt: ${PROMPT:0:50}..."
echo "Requests: ${NUM_REQUESTS}"
echo ""

benchmark_endpoint() {
    local name=$1
    local url=$2
    local total_tokens=0
    local total_time=0
    
    echo "--- Testing ${name} ---"
    
    for i in $(seq 1 ${NUM_REQUESTS}); do
        start=$(date +%s.%N)
        response=$(curl -s -X POST "${url}/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -d "{\"model\": \"test\", \"messages\": [{\"role\": \"user\", \"content\": \"${PROMPT}\"}], \"max_tokens\": 200}")
        end=$(date +%s.%N)
        
        tokens=$(echo "$response" | jq -r '.usage.completion_tokens // 0')
        elapsed=$(echo "$end - $start" | bc)
        
        if [[ "$tokens" -gt 0 ]]; then
            total_tokens=$((total_tokens + tokens))
            total_time=$(echo "$total_time + $elapsed" | bc)
            tps=$(echo "scale=2; $tokens / $elapsed" | bc)
            echo "  Request $i: ${tokens} tokens in ${elapsed}s (${tps} tok/s)"
        else
            echo "  Request $i: FAILED"
        fi
    done
    
    if [[ "$total_tokens" -gt 0 ]]; then
        avg_tps=$(echo "scale=2; $total_tokens / $total_time" | bc)
        echo ""
        echo "${name} Summary:"
        echo "  Total tokens: ${total_tokens}"
        echo "  Total time: ${total_time}s"
        echo "  Average: ${avg_tps} tok/s"
    fi
    echo ""
}

# Check endpoints
echo "Checking endpoints..."
llama_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
kt_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8005/health 2>/dev/null || echo "000")

if [[ "$llama_status" == "200" ]]; then
    echo "✓ llama.cpp (8000): OK"
else
    echo "✗ llama.cpp (8000): Not responding"
fi

if [[ "$kt_status" == "200" ]]; then
    echo "✓ KT+SGLang (8005): OK"
else
    echo "✗ KT+SGLang (8005): Not responding"
fi
echo ""

# Run benchmarks
if [[ "$llama_status" == "200" ]]; then
    benchmark_endpoint "llama.cpp" "http://localhost:8000"
fi

if [[ "$kt_status" == "200" ]]; then
    benchmark_endpoint "KT+SGLang" "http://localhost:8005"
fi

echo "=== Benchmark Complete ==="
