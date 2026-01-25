#!/bin/bash
set -e

echo "=========================================="
echo "OPERATION BLEEDING EDGE: Docker Build"
echo "=========================================="

cd "$(dirname "$0")/.."

echo "[1/3] Building Docker image..."
docker build \
    -f docker/Dockerfile.bleeding-edge \
    -t omni/engine:bleeding_edge \
    docker/

echo "[2/3] Verifying image..."
docker run --rm omni/engine:bleeding_edge python3 -c "
import torch
import sglang
import kt_kernel
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print('sglang: OK')
print('kt_kernel: OK')
"

echo "[3/3] Image ready!"
docker images | grep bleeding_edge

echo "=========================================="
echo "Deploy with: kubectl apply -f k8s/bleeding-edge-deploy.yaml"
echo "=========================================="
