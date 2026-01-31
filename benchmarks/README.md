# Benchmark Results

Performance baselines for Protocol OMNI inference optimization.

## Directory Structure

```
benchmarks/
├── benchmark-sweep.sh              # Parameter sweep tool (wraps llama-bench)
├── 2026-01-28-pre-optimization/    # Baseline before BIOS tuning
│   ├── settings.txt                # System state snapshot
│   └── benchmark-results.txt       # Inference performance metrics
├── 2026-01-29-baseline/            # BIOS baseline documentation
└── YYYY-MM-DD_HHMMSS-sweep/        # Generated sweep results
    ├── llama-bench-results.json    # Raw benchmark data
    ├── gpu-telemetry.jsonl         # GPU state snapshots
    ├── config.json                 # Sweep configuration
    └── summary.md                  # Human-readable summary
```

## Parameter Sweep Tool

`benchmark-sweep.sh` wraps the official `llama-bench` with GPU telemetry for systematic parameter optimization.

### Quick Start

```bash
# Deploy to server
scp benchmarks/benchmark-sweep.sh omni@100.94.47.77:/home/omni/

# Run quick sweep (~5 min)
ssh omni@100.94.47.77 "./benchmark-sweep.sh quick"

# Run full sweep (~30 min)
ssh omni@100.94.47.77 "./benchmark-sweep.sh full"

# Run KV cache comparison
ssh omni@100.94.47.77 "./benchmark-sweep.sh kv /path/to/model.gguf"

# Custom sweep
ssh omni@100.94.47.77 "SWEEP_NGL=5,10,15 SWEEP_FA=0,1 SWEEP_CTK=f16,q4_1 ./benchmark-sweep.sh custom"
```

### Presets

| Preset | Duration | Parameters Varied |
|--------|----------|-------------------|
| `quick` | ~5 min | fa, ctk (limited) |
| `full` | ~30 min | ngl, batch, ubatch, fa, ctk, split_mode |
| `kv` | ~10 min | KV cache types only |
| `ngl` | ~15 min | GPU layers only |
| `batch` | ~15 min | Batch sizes only |
| `multigpu` | ~20 min | Tensor split ratios (INFORMATIONAL ONLY) |
| `custom` | varies | Via SWEEP_* env vars |

### Architecture Note (S-021, S-031)

For asymmetric VRAM (96GB + 32GB), **INDEPENDENT WORKLOADS are optimal**:
- **S-021 tested**: tensor-split `75,25` = 8.26 tok/s vs single GPU = 11.74 tok/s (**-30% WORSE**)
- Tensor split (`-ts`) adds PCIe overhead and wastes VRAM on the larger GPU
- The `multigpu` preset is for verification only — NOT for production
- See `docs/research/2026-01-31-dual-gpu-optimization-deep-research.md`

### Environment Variables (for `custom` preset)

| Variable | Default | Description |
|----------|---------|-------------|
| `SWEEP_NGL` | 10 | GPU layers (comma-separated or range) |
| `SWEEP_BATCH` | 2048 | Batch sizes |
| `SWEEP_UBATCH` | 512 | Micro-batch sizes |
| `SWEEP_FA` | 0,1 | Flash attention (0=off, 1=on) |
| `SWEEP_CTK` | f16,q4_1 | KV cache types |
| `SWEEP_SM` | none | Split mode (none, layer, row) |
| `SWEEP_TS` | (empty) | Tensor split values, semicolon-separated (e.g., `;75,25;65,35`) |
| `SWEEP_REPS` | 3 | Repetitions per config |
| `LLAMA_BENCH` | /opt/llama.cpp-mxfp4/build/bin/llama-bench | Path to llama-bench |

**Note on SWEEP_TS format**: Each value is comma-separated GPU weights (e.g., `75,25` means 75% GPU0, 25% GPU1). Use semicolons to separate different configurations to test. An empty segment means single-GPU (no tensor split).

### Output

Each sweep creates a timestamped directory with:
- `llama-bench-results.json` — Raw benchmark data
- `llama-bench.log` — Benchmark stderr/progress output
- `gpu-telemetry.jsonl` — Pre/post GPU state (JSONL format: temp, power, ECC, clocks)
- `config.json` — Sweep configuration
- `summary.md` — Human-readable results table with best config

---

## Current Baseline (2026-01-28)

| Metric | Short Prompt | Long Prompt |
|--------|--------------|-------------|
| Prompt Eval | 23.14 tok/s | 10.77 tok/s |
| Generation | **11.35 tok/s** | 10.89 tok/s |

### Configuration
- **Model**: DeepSeek-R1-0528 Q4_K_M (671B)
- **llama.cpp**: b7848 with MLA + KV cache q4_1
- **GPUs**: RTX 5090 (32GB) + RTX PRO 6000 (96GB)
- **CPU Governor**: performance (changed from powersave)
- **GPU Clocks**: Locked at 2100 MHz minimum

## Pending Optimizations

### BIOS Changes (Conservative)
| Setting | Current | Target |
|---------|---------|--------|
| PBO PPT | Stock (350W) | 700W |
| PBO TDC | Stock | 550A |
| PBO EDC | Stock | 700A |
| Curve Optimizer | None | All-Core -20 |
| FCLK | Auto | 2000 MHz |

### Expected Gains
- **PBO + Curve Optimizer**: +10-15%
- **Memory Timings**: +3-5%
- **Total Expected**: +15-25% over current baseline

## Running Benchmarks

```bash
# Run benchmark and save results
./scripts/run-benchmark.sh

# Compare two benchmark runs
./scripts/compare-benchmarks.sh baseline_dir optimized_dir
```

## Persistence Scripts

After reboot, optimizations are preserved via systemd:
- `/etc/systemd/system/cpu-perf.service` - CPU governor
- `/etc/systemd/system/gpu-perf.service` - GPU clock locks

Install on target host:
```bash
sudo cp scripts/persistence/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cpu-perf gpu-perf
```
