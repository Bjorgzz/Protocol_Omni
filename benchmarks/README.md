# Benchmark Results

Performance baselines for Protocol OMNI inference optimization.

## Directory Structure

```
benchmarks/
├── 2026-01-28-pre-optimization/   # Baseline before BIOS tuning
│   ├── settings.txt               # System state snapshot
│   └── benchmark-results.txt      # Inference performance metrics
└── YYYY-MM-DD-post-optimization/  # After applying optimizations (TBD)
```

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
