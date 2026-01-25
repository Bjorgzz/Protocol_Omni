# Protocol OMNI - Infrastructure Reference

## Hardware Target

- **Host:** `192.168.3.10` (omni-prime)
- **User/Pass:** `omni` / `135610aa`
- **BMC:** `192.168.3.202` (`admin` / `Aa135610`)

## Compute Resources

| Component | Spec |
|-----------|------|
| CPU | AMD Threadripper 9995WX (96 cores, Zen5 AVX-512) |
| RAM | 384GB DDR5-6400 (ECC), **NPS=1 (Unified NUMA)** |
| GPU0 | RTX PRO 6000 Blackwell 96GB @ f1:00.0 |
| GPU1 | RTX 5090 32GB @ 11:00.0 |
| Storage | 2x 4TB NVMe Gen5 |

## Inference Engine: llama.cpp (Concrete Bunker Doctrine)

**Engine:** llama.cpp with sm_120 (Blackwell) CUDA kernels. Selected for stability and native flash attention support.

```bash
# DeepSeek-V3.2 launch parameters
--n-gpu-layers 19 \
--tensor-split 75,25 \
--ctx-size 8192
```

**Performance:**
- Generation: 10.75 tok/s (above 7.57 target)
- Prompt eval: ~100 tok/s

## NUMA Configuration (CRITICAL)

```bash
numactl --cpunodebind=0 --interleave=all <command>
```

- `--cpunodebind=0`: Pins threads to Node 0
- `--interleave=all`: Spreads memory across all 4 nodes (enables 384GB)

**WARNING:** Never use `--membind=0` - limits to 96GB, causes OOM

## VRAM Allocation

| GPU | Allocated | Model |
|-----|-----------|-------|
| Blackwell 96GB | 91GB | DeepSeek-V3.2 primary layers (19 layers) |
| 5090 32GB | 26GB | DeepSeek-V3.2 overflow |
| CPU RAM | ~200GB | Cold MoE experts |

## Service Ports

| Service | Port | Profile | Notes |
|---------|------|---------|-------|
| DeepSeek-V3.2 | 8000 | default | Primary Oracle |
| Kimi K2 | 8001 | full | **MUTUALLY EXCLUSIVE with TRT-Sandbox** |
| Qwen Executor | 8002 | cpu-executor | CPU-only, 192 threads |
| DeepSeek-MXFP4 | 8003 | mxfp4-bench | Experimental benchmark sidecar |
| Mem0 | 8050 | default | Persistent memory |
| MCP Proxy | 8070 | default | Security gateway |
| Agent Orchestrator | 8080 | default | LangGraph router |
| Metacognition | 8011 | default | 4-gate verification |
| GEPA Engine | 8010 | default | Prompt evolution |
| Phoenix | 6006 | default | OTEL observability |
| Grafana | 3000 | default | Dashboards |
| Prometheus | 9090 | default | Metrics |
| Qdrant | 6333 | default | Vector store |
| Memgraph | 7687 | default | Code knowledge graph |
| Letta | 8283 | default | Self-improvement |
| TRT-Sandbox | 8001 | trt-sandbox | **MUTUALLY EXCLUSIVE with Kimi K2** |

**Port 8001 Conflict:** Kimi K2 (profile: full) and TRT-Sandbox (profile: trt-sandbox) share port 8001. These profiles are mutually exclusive - never enable both simultaneously.

## Cognitive Models (Extended)

| Model | Role | Profile | Status |
|-------|------|---------|--------|
| DeepSeek-V3.2 | Primary Oracle | default | LIVE |
| Qwen2.5-Coder-7B | CPU Executor | cpu-executor | LIVE |
| Kimi K2 | External Tool Orchestrator | full | Optional |
| MiniMax M2.1 | Emergency Failsafe | emergency | Cold Storage |

## Network Isolation

| Network | Subnet | Purpose |
|---------|--------|---------|
| omni-network | 172.30.0.0/16 | General inter-service communication |
| internal_brain | 172.31.0.0/16 | Inference isolation (see notes) |

**internal_brain Network Notes:**
- `deepseek-v32`: Primary Oracle, isolated from direct external egress
- `mcp-proxy`: Gateway to internal_brain; has dual-network membership (omni-network + internal_brain) to broker tool requests
- `mem0`: Memory layer for Oracle; dual-network for Qdrant access
- `trt-sandbox`: Isolated testing environment

**Intent:** Oracle (DeepSeek) cannot make direct external calls. All tool invocations route through mcp-proxy which validates and rate-limits requests.

## Key Directories (Remote)

| Path | Purpose |
|------|---------|
| `/nvme/models/` | Model weights |
| `/nvme/prompts/` | System prompts |
| `/nvme/letta/` | Letta agent state |
| `/nvme/mem0/` | Mem0 persistent data |
| `/nvme/phoenix-data/` | Phoenix traces |
| `~/Protocol_Omni/docker/` | Docker Compose stacks |
| `~/Protocol_Omni/src/` | Python source |
| `~/Protocol_Omni/config/` | Configuration files |