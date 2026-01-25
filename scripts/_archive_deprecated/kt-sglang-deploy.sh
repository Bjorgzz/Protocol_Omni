#!/bin/bash
# KTransformers + SGLang Deployment Script
# Protocol OMNI v15.0 - KT Evaluation
#
# Prerequisites:
#   - BF16 weights at /nvme/models/deepseek-v3.2-bf16/
#   - AMD BLIS built at /nvme/blis-install/
#   - ktransformers conda environment with PyTorch cu124+
#
# Usage: ./kt-sglang-deploy.sh

set -e

# Configuration
CONDA_ENV="/nvme/miniconda3/envs/ktransformers"
BLIS_PATH="/nvme/blis-install"
MODEL_PATH="/nvme/models/deepseek-v3.2-bf16"
INT4_PATH="/nvme/models/deepseek-v3.2-kt-int4"
KT_PATH="/nvme/build/ktransformers"
PORT=8005

echo "=== KTransformers + SGLang Deployment ==="

# Activate environment
source /nvme/miniconda3/bin/activate ktransformers

# Set environment variables
export CPUINFER_ENABLE_BLIS=ON
export BLIS_INSTALL_PATH="${BLIS_PATH}"
export LD_LIBRARY_PATH="${BLIS_PATH}/lib:${LD_LIBRARY_PATH}"
export SGLANG_ENABLE_JIT_DEEPGEMM=false

# Verify BLIS
if [[ ! -f "${BLIS_PATH}/lib/libblis.so" ]]; then
    echo "ERROR: BLIS not found at ${BLIS_PATH}"
    exit 1
fi
echo "✓ BLIS found"

# Verify model weights
if [[ ! -d "${MODEL_PATH}" ]]; then
    echo "ERROR: Model not found at ${MODEL_PATH}"
    exit 1
fi
SAFETENSOR_COUNT=$(find "${MODEL_PATH}" -name "*.safetensors" 2>/dev/null | wc -l)
echo "✓ Found ${SAFETENSOR_COUNT} safetensor files"

# Check if weight conversion is needed
if [[ ! -d "${INT4_PATH}" ]] || [[ $(find "${INT4_PATH}" -name "*.bin" 2>/dev/null | wc -l) -eq 0 ]]; then
    echo "Converting weights to INT4 (this may take 1-2 hours)..."
    python -m ktransformers.kt_kernel.scripts.convert_cpu_weights \
        --input-path "${MODEL_PATH}" \
        --input-type bf16 \
        --output "${INT4_PATH}" \
        --quant-method int4
    echo "✓ Weight conversion complete"
else
    echo "✓ INT4 weights already exist"
fi

# Launch SGLang server with Kebob workarounds for Blackwell sm_120
echo "Launching SGLang server on port ${PORT}..."
python -m sglang.launch_server \
    --model-path "${INT4_PATH}" \
    --port ${PORT} \
    --host 0.0.0.0 \
    --kt-method MOE_INT8 \
    --kt-cpuinfer 192 \
    --kt-threadpool-count 4 \
    --kt-num-gpu-experts 24 \
    --attention-backend flashinfer \
    --kv-cache-dtype bf16 \
    --tensor-parallel-size 2 \
    --trust-remote-code

echo "Server started on http://0.0.0.0:${PORT}"
