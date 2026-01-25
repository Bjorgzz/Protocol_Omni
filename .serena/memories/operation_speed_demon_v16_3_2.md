# Operation Speed Demon - MXFP4 Benchmark (v16.3.2)

## Status: IN PROGRESS - Download Running

### Mission
Benchmark MXFP4 quantization vs Q3_K_M to validate >15 tok/s target (current baseline: 10.9 tok/s).

### Critical Corrections Applied
| Original Plan | Problem | Corrected Approach |
|---------------|---------|-------------------|
| Rebuild llama.cpp with MXFP4 flags | Binary already has MXFP4 support | Use existing `omni/llama-server:sm120-cuda13` |
| Use SM90 architecture | SM90 = Hopper (H100), not Blackwell | SM120 already configured |
| Build in Docker | VMM disabled = 3x regression | No rebuild needed |
| Quantize model manually | Takes hours | Download pre-quantized from HuggingFace |

### Infrastructure Ready
1. **Docker Sidecar**: `deepseek-mxfp4` service in `docker/omni-stack.yaml`
   - Profile: `mxfp4-bench` (isolated from default)
   - Port: 8003 (production uses 8000)
   - Uses same image: `omni/llama-server:sm120-cuda13`

2. **Benchmark Script**: `scripts/benchmark_dragrace.py` (246 lines)
   - Measures tokens/second for 500-word essay generation
   - Supports single endpoint and comparison modes
   - Saves results to `/tmp/dragrace_results.json`

3. **Model Download**: Running with hf_transfer acceleration
   - Source: `stevescot1979/DeepSeek-V3.2-MXFP4-GGUF` (341GB)
   - Destination: `/nvme/models/deepseek-v3.2-mxfp4/`
   - Speed: **57 MB/s** (9.5x improvement with hf_transfer)
   - ETA: ~100 minutes from start
   - Screen: `172040.mxfp4_turbo`
   - Monitor: `tail -f /tmp/mxfp4_turbo.log`

### Benchmark Procedure (After Download)
```bash
# 1. Benchmark production (Q3_K_M)
python3 ~/Protocol_Omni/scripts/benchmark_dragrace.py --port 8000 --name "Q3_K_M"

# 2. Stop production, start MXFP4
cd ~/Protocol_Omni/docker
docker compose -f omni-stack.yaml stop deepseek-v32
docker compose -f omni-stack.yaml --profile mxfp4-bench up -d deepseek-mxfp4
# Wait 10 minutes for model loading...
curl http://localhost:8003/health

# 3. Benchmark MXFP4
python3 ~/Protocol_Omni/scripts/benchmark_dragrace.py --port 8003 --name "MXFP4"

# 4. Restore production
docker compose -f omni-stack.yaml stop deepseek-mxfp4
docker compose -f omni-stack.yaml up -d deepseek-v32
```

### Remote Host Connection
- Host: `192.168.3.10`
- User: `omni`
- Password: `135610aa`
- SSH key auth was timing out; password auth works

### Key Files Modified
- `docker/omni-stack.yaml` - Added deepseek-mxfp4 sidecar service
- `scripts/benchmark_dragrace.py` - New benchmark tool
- `docs/roadmap_phase_4_5.md` - Updated to v16.3.2

### Next Actions
1. Wait for download completion (~100 min from 2026-01-24 20:21 UTC)
2. Execute benchmark procedure above
3. Compare results: Q3_K_M (10.9 tok/s) vs MXFP4 (target >15 tok/s)
4. Document findings and curate to ByteRover
