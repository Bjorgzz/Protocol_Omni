#!/bin/bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <baseline_dir> <optimized_dir>"
  echo "Example: $0 ~/benchmarks/2026-01-28-pre-optimization ~/benchmarks/2026-01-28-post-optimization"
  exit 1
fi

BASELINE="$1/benchmark-results.txt"
OPTIMIZED="$2/benchmark-results.txt"

if [ ! -f "$BASELINE" ]; then
  echo "Error: Baseline file not found: $BASELINE"
  exit 1
fi

if [ ! -f "$OPTIMIZED" ]; then
  echo "Error: Optimized file not found: $OPTIMIZED"
  exit 1
fi

echo "=== Benchmark Comparison ==="
echo "Baseline:  $BASELINE"
echo "Optimized: $OPTIMIZED"
echo ""

echo "=== Baseline Results ==="
grep -E "tok/s|Generation" "$BASELINE" | tail -5 || echo "(no matching lines)"
echo ""

echo "=== Optimized Results ==="
grep -E "tok/s|Generation" "$OPTIMIZED" | tail -5 || echo "(no matching lines)"
echo ""

extract_gen_speed() {
  grep "Generation:" "$1" 2>/dev/null | head -1 | sed 's/.*@ *\([0-9.]*\) *tok\/s.*/\1/' || true
}

BASE_GEN=$(extract_gen_speed "$BASELINE")
OPT_GEN=$(extract_gen_speed "$OPTIMIZED")

if [ -n "$BASE_GEN" ] && [ -n "$OPT_GEN" ]; then
  if command -v bc &>/dev/null; then
    IMPROVEMENT=$(echo "scale=2; (($OPT_GEN - $BASE_GEN) / $BASE_GEN) * 100" | bc)
  else
    IMPROVEMENT=$(python3 -c "print(f'{(($OPT_GEN - $BASE_GEN) / $BASE_GEN) * 100:.2f}')" 2>/dev/null || echo "N/A")
  fi
  echo "=== Summary ==="
  echo "Baseline Generation:  $BASE_GEN tok/s"
  echo "Optimized Generation: $OPT_GEN tok/s"
  echo "Improvement: $IMPROVEMENT%"
else
  echo "=== Summary ==="
  echo "Could not extract generation speeds for comparison."
  echo "Ensure both files contain 'Generation: X tokens @ Y.YY tok/s' lines."
fi
