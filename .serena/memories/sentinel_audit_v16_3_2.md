# Sentinel Audit v16.3.2 (2026-01-24)

## NVIDIA Driver Analysis

| Component | Current | Available | Action |
|-----------|---------|-----------|--------|
| Driver | 580.95.05 | **580.126.09** | UPGRADE POST-BENCHMARK |
| nvidia-container-toolkit | 1.18.1 | 1.18.2 | Minor update |

### 580.126.09 Key Fixes (Released Jan 13, 2026)
- **Buffer Scrubbing Performance**: Affects 671B model loading
- **kvmalloc() Migration**: Better memory allocation on 64K kernels
- **NVLink Partition Modes**: Relevant for multi-GPU (96GB + 32GB)
- **cudaErrorNoDevice Stack Fix**: Prevents corruption during deinit
- **GPU Health after Link State Changes**: Important for tensor-split

## Python Stack

| Package | Current | Latest | Action |
|---------|---------|--------|--------|
| langgraph | ≥1.0.3 | **1.0.7** | UPDATE |
| mem0ai | ≥1.0.2 | **1.0.5** | UPDATE |
| fastapi | 0.128.0 | 0.116.1? | VERIFY (version anomaly) |
| httpx | ≥0.28.0 | 0.28.1 | KEEP |
| arize-phoenix-otel | ≥0.14.0 | current | KEEP |

### LangGraph 1.0.7 Changes
- `wrap_model_call` dynamic tool calling
- aiosqlite breaking change fix

## Docker Images - :latest Anti-Pattern

**7 images using `:latest`** (violates supply chain doctrine):
- `letta/letta:latest`
- `memgraph/memgraph-mage:latest`
- `qdrant/qdrant:latest`
- `prom/prometheus:latest`
- `grafana/grafana:latest`
- `arizephoenix/phoenix:latest`
- `nvcr.io/nvidia/k8s/dcgm-exporter:latest`

**Action**: Pin all to specific versions in maintenance window.

## Operational Issues

| Service | Status | Issue |
|---------|--------|-------|
| memgraph | Restarting (139) | **SIGSEGV crash loop** - URGENT |
| deepseek-v32 | unhealthy | Normal (slow healthcheck for 671B) |
| mcp-proxy | unhealthy | Needs investigation |
| qdrant | unhealthy | Needs investigation |

## MXFP4 Intelligence

| Finding | Source |
|---------|--------|
| MXFP4 retains 99.5% accuracy on DeepSeek | AMD ROCm Blog |
| MXFP4 up to 25% faster on Blackwell | Reddit LocalLLaMA |
| vLLM MXFP4 slower than llama.cpp | NVIDIA Forums |

## Priority Actions

1. **P0**: Fix memgraph crash (pin to stable version)
2. **P1**: Complete MXFP4 benchmark (download: 4.8GB/341GB)
3. **P2**: Update langgraph>=1.0.7, mem0ai>=1.0.5
4. **P3**: Upgrade NVIDIA 580.126.09 post-benchmark
5. **P3**: Pin Docker images to versions

## Stack Health: 85% Current
