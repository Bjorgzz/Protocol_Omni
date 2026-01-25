#!/usr/bin/env python3
"""
Operation Speed Demon: MXFP4 vs Q3_K_M Drag Race Benchmark

Protocol OMNI v16.3.2 - Benchmarks both quantization methods
and reports tokens_per_second comparison.

Usage:
    # Benchmark production (Q3_K_M on :8000)
    python benchmark_dragrace.py --port 8000 --name "Q3_K_M"
    
    # Benchmark experimental (MXFP4 on :8003)
    python benchmark_dragrace.py --port 8003 --name "MXFP4"
    
    # Compare both (sequential, requires service switch between runs)
    python benchmark_dragrace.py --compare
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional

import httpx

BENCHMARK_PROMPT = """Write a 500-word essay on the history of GPUs. Cover:
1. The origins of graphics processing in the 1980s
2. The emergence of dedicated GPU hardware in the 1990s (NVIDIA, ATI)
3. The programmable shader revolution (2001-2010)
4. GPGPU and CUDA transforming scientific computing (2007-2015)
5. The deep learning explosion and AI accelerators (2016-present)
6. Future trends: Ray tracing, tensor cores, and specialized AI chips
Include specific product names, dates, and technical milestones."""

HOST = "192.168.3.10"
TIMEOUT = 300  # 5 minutes for 671B model


@dataclass
class BenchmarkResult:
    name: str
    port: int
    prompt_tokens: int
    completion_tokens: int
    total_time_s: float
    tokens_per_second: float
    prompt_eval_per_second: Optional[float] = None
    error: Optional[str] = None


def benchmark_endpoint(port: int, name: str) -> BenchmarkResult:
    """Run benchmark against a single endpoint."""
    url = f"http://{HOST}:{port}/v1/chat/completions"
    
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": BENCHMARK_PROMPT}],
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": False,
    }
    
    print(f"\n{'='*60}")
    print(f"Benchmarking {name} on port {port}...")
    print(f"Prompt: {len(BENCHMARK_PROMPT)} chars")
    print(f"Max tokens: {payload['max_tokens']}")
    print(f"{'='*60}")
    
    start_time = time.perf_counter()
    
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            
        elapsed = time.perf_counter() - start_time
        data = response.json()
        
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Calculate tokens per second
        tps = completion_tokens / elapsed if elapsed > 0 else 0
        
        # Get model info
        model = data.get("model", "unknown")
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"\nResponse received from: {model}")
        print(f"Response length: {len(content)} chars")
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Tokens/second: {tps:.2f}")
        
        return BenchmarkResult(
            name=name,
            port=port,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_time_s=elapsed,
            tokens_per_second=tps,
        )
        
    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start_time
        return BenchmarkResult(
            name=name,
            port=port,
            prompt_tokens=0,
            completion_tokens=0,
            total_time_s=elapsed,
            tokens_per_second=0,
            error=f"Timeout after {elapsed:.1f}s",
        )
    except httpx.HTTPStatusError as e:
        return BenchmarkResult(
            name=name,
            port=port,
            prompt_tokens=0,
            completion_tokens=0,
            total_time_s=0,
            tokens_per_second=0,
            error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return BenchmarkResult(
            name=name,
            port=port,
            prompt_tokens=0,
            completion_tokens=0,
            total_time_s=0,
            tokens_per_second=0,
            error=str(e),
        )


def print_comparison(results: list[BenchmarkResult]):
    """Print comparison table of results."""
    print("\n" + "="*70)
    print("OPERATION SPEED DEMON: BENCHMARK RESULTS")
    print("="*70)
    print(f"{'Model':<15} {'Port':<8} {'Tokens':<10} {'Time (s)':<12} {'Tok/s':<10} {'Status':<10}")
    print("-"*70)
    
    for r in results:
        if r.error:
            print(f"{r.name:<15} {r.port:<8} {'N/A':<10} {'N/A':<12} {'N/A':<10} ERROR")
            print(f"    Error: {r.error}")
        else:
            print(f"{r.name:<15} {r.port:<8} {r.completion_tokens:<10} {r.total_time_s:<12.2f} {r.tokens_per_second:<10.2f} OK")
    
    print("-"*70)
    
    # Calculate speedup if both succeeded
    valid = [r for r in results if not r.error]
    if len(valid) >= 2:
        baseline = next((r for r in valid if "Q3" in r.name), valid[0])
        experimental = next((r for r in valid if r != baseline), valid[1])
        
        if baseline.tokens_per_second > 0:
            speedup = experimental.tokens_per_second / baseline.tokens_per_second
            print(f"\nSpeedup: {experimental.name} is {speedup:.2f}x vs {baseline.name}")
            
            if speedup > 1.0:
                print(f"WINNER: {experimental.name} ({(speedup-1)*100:.1f}% faster)")
            elif speedup < 1.0:
                print(f"WINNER: {baseline.name} ({(1/speedup-1)*100:.1f}% faster)")
            else:
                print("TIE: Both perform equally")
    
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="MXFP4 vs Q3_K_M Drag Race")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--name", type=str, default="production", help="Benchmark name")
    parser.add_argument("--compare", action="store_true", help="Run comparison mode")
    parser.add_argument("--host", type=str, default=HOST, help="Server host")
    args = parser.parse_args()
    
    global HOST
    HOST = args.host
    
    if args.compare:
        # Sequential comparison mode
        print("OPERATION SPEED DEMON: DRAG RACE BENCHMARK")
        print("="*60)
        print("\nThis benchmark requires manual service switching.")
        print("Both services share GPU memory and cannot run simultaneously.")
        print("\n1. First, we'll benchmark the current production service (Q3_K_M)")
        print("2. Then you'll need to switch to MXFP4:")
        print("   cd ~/Protocol_Omni/docker")
        print("   docker compose -f omni-stack.yaml stop deepseek-v32")
        print("   docker compose -f omni-stack.yaml --profile mxfp4-bench up -d deepseek-mxfp4")
        print("3. Finally, we'll benchmark MXFP4")
        
        input("\nPress Enter to start Q3_K_M benchmark...")
        r1 = benchmark_endpoint(8000, "Q3_K_M")
        
        print("\n" + "="*60)
        print("Q3_K_M benchmark complete. Now switch to MXFP4:")
        print("  cd ~/Protocol_Omni/docker")
        print("  docker compose -f omni-stack.yaml stop deepseek-v32")
        print("  docker compose -f omni-stack.yaml --profile mxfp4-bench up -d deepseek-mxfp4")
        print("  # Wait 10 minutes for model loading...")
        print("  curl http://localhost:8003/health")
        input("\nPress Enter when MXFP4 is ready (port 8003)...")
        
        r2 = benchmark_endpoint(8003, "MXFP4")
        
        print_comparison([r1, r2])
        
        # Save results
        results = {
            "benchmark": "speed_demon_dragrace",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {
                    "name": r.name,
                    "port": r.port,
                    "tokens_per_second": r.tokens_per_second,
                    "completion_tokens": r.completion_tokens,
                    "total_time_s": r.total_time_s,
                    "error": r.error,
                }
                for r in [r1, r2]
            ],
        }
        
        with open("/tmp/dragrace_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to /tmp/dragrace_results.json")
        
    else:
        # Single endpoint mode
        result = benchmark_endpoint(args.port, args.name)
        print_comparison([result])


if __name__ == "__main__":
    main()
