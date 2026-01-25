#!/bin/bash
# KTransformers Build Script - The Long Game
# Builds custom KTransformers with DeepGEMM optimizations for 671B inference

set -e

BUILD_DIR="/workspace/builds"
REPO_URL="https://github.com/kvcache-ai/ktransformers.git"

echo "=== KTransformers Build Script ==="
echo "Target: DeepSeek-V3 671B inference engine"
echo "Started at: $(date)"

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Clone if not exists
if [ ! -d "ktransformers" ]; then
    echo "[1/4] Cloning KTransformers repository..."
    git clone "$REPO_URL"
else
    echo "[1/4] Repository exists, pulling latest..."
    cd ktransformers && git pull && cd ..
fi

cd ktransformers

# Try DeepGEMM branch first, fallback to main
echo "[2/4] Checking out DeepGEMM optimized branch..."
if git checkout v0.3-deepgemm 2>/dev/null; then
    echo "Using v0.3-deepgemm branch"
elif git checkout deepgemm 2>/dev/null; then
    echo "Using deepgemm branch"
else
    echo "DeepGEMM branch not found, using main"
    git checkout main
fi

# Build Docker image
echo "[3/4] Building Docker image (this may take 30+ minutes)..."
docker build -t local/ktransformers:custom .

echo "[4/4] Build complete!"
echo "Image: local/ktransformers:custom"
echo "Finished at: $(date)"
echo ""
echo "Next steps:"
echo "  1. Push image to registry or load directly"
echo "  2. Update k8s/ktransformers-stack.yaml"
echo "  3. Deploy for 671B inference"
