#!/bin/bash
# Protocol OMNI: Metal Build Container
# Packages bare metal llama.cpp binaries into Docker image
#
# Prerequisites:
#   - Bare metal build at ~/llama_build/build/bin/
#   - Docker installed and running
#
# Usage:
#   ./scripts/build-metal-container.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STAGING_DIR="/tmp/llama-metal-staging"
BUILD_DIR="${LLAMA_BUILD_DIR:-/home/omni/llama_build/build}"

echo "=== Protocol OMNI: Metal Build Container ==="
echo "Build dir: $BUILD_DIR"
echo "Staging dir: $STAGING_DIR"
echo ""

# Clean and create staging directory
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/bin" "$STAGING_DIR/lib"

# Copy binaries (resolve symlinks with -L)
echo "[1/4] Copying binaries..."
cp -L "$BUILD_DIR/bin/llama-server" "$STAGING_DIR/bin/"
cp -L "$BUILD_DIR/bin/llama-bench" "$STAGING_DIR/bin/"
cp -L "$BUILD_DIR/bin/llama-cli" "$STAGING_DIR/bin/"

# Copy shared libraries (resolve symlinks, preserve as .so.0)
echo "[2/4] Copying shared libraries..."
for lib in libggml libggml-base libggml-cpu libggml-cuda libllama; do
    # Find the actual versioned file
    versioned=$(ls "$BUILD_DIR/bin/${lib}.so."*[0-9] 2>/dev/null | head -1 || true)
    if [ -z "$versioned" ]; then
        # Try with longer version suffix
        versioned=$(ls "$BUILD_DIR/bin/${lib}.so."* 2>/dev/null | grep -v "^$BUILD_DIR/bin/${lib}.so$" | head -1)
    fi
    if [ -n "$versioned" ]; then
        cp -L "$versioned" "$STAGING_DIR/lib/${lib}.so"
        echo "  - ${lib}.so (from $(basename $versioned))"
    else
        echo "  - WARNING: ${lib}.so not found"
    fi
done

# Verify VMM support in CUDA library
echo "[3/4] Verifying VMM support..."
if strings "$STAGING_DIR/lib/libggml-cuda.so" | grep -q "cuMemCreate"; then
    echo "  - VMM symbols found (cuMemCreate present)"
else
    echo "  - WARNING: VMM symbols may be disabled"
fi

# Verify SM120 kernels
if cuobjdump "$STAGING_DIR/lib/libggml-cuda.so" 2>/dev/null | grep -q "sm_120"; then
    echo "  - SM120 kernels found"
else
    echo "  - WARNING: SM120 kernels not detected"
fi

echo "[4/4] Building Docker image..."
cd "$PROJECT_ROOT"

# Create minimal Dockerfile that copies from staging
cat > "$STAGING_DIR/Dockerfile" << 'EOF'
FROM nvidia/cuda:13.0.0-runtime-ubuntu24.04

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libcurl4t64 \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /opt/llama.cpp/build/bin

# Copy binaries
COPY bin/llama-server /opt/llama.cpp/build/bin/
COPY bin/llama-bench /opt/llama.cpp/build/bin/
COPY bin/llama-cli /opt/llama.cpp/build/bin/

# Copy shared libraries
COPY lib/*.so /usr/local/lib/

# Update library cache
RUN ldconfig

# Environment setup
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV PATH=/opt/llama.cpp/build/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD wget -q --spider http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/opt/llama.cpp/build/bin/llama-server"]
CMD ["--help"]
EOF

# Build from staging directory
docker build -t omni/llama-server:sm120-vmm "$STAGING_DIR"

echo ""
echo "=== Build Complete ==="
echo "Image: omni/llama-server:sm120-vmm"
echo ""
echo "To deploy:"
echo "  docker tag omni/llama-server:sm120-vmm omni/llama-server:sm120-cuda13"
echo "  cd docker && docker compose -f omni-stack.yaml up -d deepseek-v32"
