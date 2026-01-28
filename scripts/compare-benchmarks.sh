#!/bin/bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <baseline_dir> <optimized_dir>"
  echo "Example: $0 ~/benchmarks/2026-01-28-pre-optimization ~/benchmarks/2026-01-28-post-optimization"
  exit 1
fi

BASELINE="$1/benchmark-results.txt"
OPTIMIZED="$2/benchmark-results.txt"

if [ ! -f "$BASELINE" ] || [ ! -r "$BASELINE" ]; then
  echo "Error: Baseline file not found or not readable: $BASELINE"
  exit 1
fi

if [ ! -f "$OPTIMIZED" ] || [ ! -r "$OPTIMIZED" ]; then
  echo "Error: Optimized file not found or not readable: $OPTIMIZED"
  exit 1
fi

echo "=== Benchmark Comparison ==="
echo "Baseline:  $BASELINE"
echo "Optimized: $OPTIMIZED"
echo ""

echo "=== Baseline Results ==="
grep -E "tok/s|Generation" "$BASELINE" | tail -5 || { rc=$?; [ $rc -eq 1 ] && echo "(no matching lines)" || exit $rc; }
echo ""

echo "=== Optimized Results ==="
grep -E "tok/s|Generation" "$OPTIMIZED" | tail -5 || { rc=$?; [ $rc -eq 1 ] && echo "(no matching lines)" || exit $rc; }
echo ""

extract_gen_speed() {
  local line
  line=$(grep -m1 "Generation:" "$1" 2>/dev/null) || true
  echo "$line" | sed -n 's/.*@ *\([0-9.]*\) *tok\/s.*/\1/p'
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
