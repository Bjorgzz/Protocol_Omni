# Operation Lazarus: KTransformers Resurrection

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Benchmark KTransformers vs llama.cpp on Threadripper/Blackwell to validate resurrection viability.

**Architecture:** Sandbox Docker container with PyTorch 2.8+ Nightly (cu128) → KTransformers → DeepSeek-V3.2

**Tech Stack:** PyTorch 2.8+ Nightly, CUDA 12.8, KTransformers, nvidia/cuda:12.8.0-devel-ubuntu22.04

---

## Executive Summary

| Item | Value |
|------|-------|
| **Objective** | Validate KTransformers on SM120 (Blackwell) |
| **Baseline** | llama.cpp @ 10.9 tok/s (Q3_K_M, NPS1) |
| **Target** | KTransformers @ >15 tok/s (speculative decoding) |
| **Intel** | PyTorch 2.8+ Nightly (cu128) adds SM120 support |
| **Risk** | Medium - Upstream fix unverified in production |

---

## Phase 1: Environment Verification

### Task 1.1: Create Dockerfile

**File:** `docker/Dockerfile.ktransformers-lazarus`

```dockerfile
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    git wget curl && \
    rm -rf /var/lib/apt/lists/*

RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PyTorch 2.8+ Nightly with cu128 (SM120 support)
RUN pip install --upgrade pip && \
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Verification checkpoint - FAIL BUILD if SM120 missing
RUN python3 -c "import torch; archs = torch.cuda.get_arch_list(); print(archs); assert 'sm_120' in archs, 'SM120 NOT FOUND'"

# KTransformers
RUN pip install ktransformers

WORKDIR /workspace
```

**Verification Command:**
```bash
docker build -f docker/Dockerfile.ktransformers-lazarus -t omni/ktransformers-sandbox:lazarus .
docker run --rm --gpus all omni/ktransformers-sandbox:lazarus \
  python3 -c "import torch; print(torch.cuda.get_arch_list())"
# Expected output includes: 'sm_120'
```

### Task 1.2: Add Docker Compose Sidecar

**File:** `docker/omni-stack.yaml` (add to services, profile: `lazarus`)

```yaml
ktransformers-lazarus:
  build:
    context: ..
    dockerfile: docker/Dockerfile.ktransformers-lazarus
  image: omni/ktransformers-sandbox:lazarus
  container_name: ktransformers-lazarus
  restart: "no"
  profiles: ["lazarus"]
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
  environment:
    CUDA_VISIBLE_DEVICES: "GPU-f4f210c1-5a52-7267-979e-fe922961190a,GPU-bfbb9aa1-3d36-b47b-988f-5752cfc54601"
  volumes:
    - /nvme/models:/models:ro
  ports:
    - "8004:8000"
  networks:
    - omni-network
```

---

## Phase 2: Benchmark Protocol

### Task 2.1: Create Benchmark Script

**File:** `scripts/benchmark_lazarus.py`

```python
#!/usr/bin/env python3
"""Operation Lazarus: KTransformers vs llama.cpp benchmark."""

import argparse
import time
import httpx
from statistics import mean, stdev

PROMPTS = [
    "Explain quantum entanglement in simple terms.",
    "Write a Python function to find prime numbers.",
    "What are the key principles of distributed systems?",
]

def benchmark_endpoint(url: str, name: str, runs: int = 3) -> dict:
    results = []
    for prompt in PROMPTS:
        for _ in range(runs):
            payload = {
                "model": "auto",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 256,
                "stream": False,
            }
            start = time.perf_counter()
            resp = httpx.post(f"{url}/v1/chat/completions", json=payload, timeout=300)
            elapsed = time.perf_counter() - start
            data = resp.json()
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            results.append({
                "tokens": tokens,
                "time": elapsed,
                "tok_s": tokens / elapsed if elapsed > 0 else 0
            })
    
    avg_tok_s = mean([r["tok_s"] for r in results])
    std_tok_s = stdev([r["tok_s"] for r in results]) if len(results) > 1 else 0
    
    return {"name": name, "avg_tok_s": avg_tok_s, "std_tok_s": std_tok_s, "runs": len(results)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Endpoint URL")
    parser.add_argument("--name", required=True, help="Engine name")
    args = parser.parse_args()
    
    result = benchmark_endpoint(args.url, args.name)
    print(f"\n{'='*50}")
    print(f"BENCHMARK RESULT: {result['name']}")
    print(f"Average: {result['avg_tok_s']:.2f} tok/s (±{result['std_tok_s']:.2f})")
    print(f"Runs: {result['runs']}")
    print(f"{'='*50}\n")
```

### Task 2.2: Execute Benchmark (Manual Procedure)

```bash
# 1. Stop llama.cpp (shared GPU memory!)
cd ~/Protocol_Omni/docker
docker compose -f omni-stack.yaml stop deepseek-v32

# 2. Start KTransformers sandbox
docker compose -f omni-stack.yaml --profile lazarus up -d ktransformers-lazarus
# Wait for model loading (~10 min)

# 3. Run benchmark
python3 ~/Protocol_Omni/scripts/benchmark_lazarus.py \
  --url http://localhost:8004 \
  --name "KTransformers (PyTorch 2.8+ cu128)"

# 4. Restore production
docker compose -f omni-stack.yaml stop ktransformers-lazarus
docker compose -f omni-stack.yaml up -d deepseek-v32
```

---

## Success Criteria

| Metric | llama.cpp Baseline | KTransformers Target | GO/NO-GO |
|--------|-------------------|---------------------|----------|
| Generation | 10.9 tok/s | >15 tok/s | GO if >12 tok/s |
| First Token | ~2s | <1.5s | GO if <2s |
| Stability | 99.9% | 99% | GO if >95% |
| VRAM | 118GB | <128GB | NO-GO if exceeds |

---

## Pivot Back Criteria

**Abort if:**
- `torch.cuda.get_arch_list()` does NOT show `sm_120`
- CUDA kernel errors on SM120
- Performance <10 tok/s (regression from llama.cpp)
- Memory exceeds 128GB VRAM budget

**Rollback:**
```bash
docker compose -f omni-stack.yaml stop ktransformers-lazarus
docker compose -f omni-stack.yaml up -d deepseek-v32
# No production changes needed - sandbox only
```

---

## Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Build sandbox container | 1 hour | ⚪ Planned |
| 2 | Verify SM120 in PyTorch | 15 min | ⚪ Planned |
| 3 | Load model in KTransformers | 30 min | ⚪ Planned |
| 4 | Run benchmark | 1 hour | ⚪ Planned |
| 5 | Document results | 30 min | ⚪ Planned |

**Total Estimate:** Half-day operation

---

## References

- **F-001:** [Lessons Learned - KTransformers](../architecture/lessons-learned.md#f-001-ktransformers-sm120-incompatibility--resurrection-candidate)
- **Intel:** PyTorch 2.8+ Nightly (cu128) verified to support SM120 (Jan 2026)
- **Baseline:** llama.cpp @ 10.9 tok/s (NPS1, Q3_K_M)

---

*Generated by Operation Lazarus Prep 2026-01-25*
