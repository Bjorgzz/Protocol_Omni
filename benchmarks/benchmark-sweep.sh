#!/usr/bin/env bash
set -euo pipefail

# Protocol OMNI Benchmark Sweep Script
# Wraps llama-bench with GPU telemetry for systematic parameter optimization
#
# Usage:
#   ./benchmark-sweep.sh [preset] [model_path]
#   ./benchmark-sweep.sh quick                    # Quick sweep (~5 min)
#   ./benchmark-sweep.sh full                     # Full sweep (~30 min)
#   ./benchmark-sweep.sh custom /path/to/model.gguf
#
# Presets:
#   quick   - Fast sanity check (limited parameter combinations)
#   full    - Complete sweep (all GPU-relevant parameters)
#   kv      - KV cache type comparison only
#   ngl     - GPU layer offload sweep only
#   custom  - Uses custom parameters from SWEEP_* env vars
#
# Architecture Note (S-021, S-031):
#   For asymmetric VRAM (96GB + 32GB), INDEPENDENT WORKLOADS are optimal.
#   Tensor split was tested: -ts 75,25 = 8.26 tok/s vs single GPU = 11.74 tok/s (-30% WORSE)
#   This tool supports -ts for verification only; production should NOT use tensor split.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
OUTPUT_DIR="${SCRIPT_DIR}/${TIMESTAMP}-sweep"

# Default paths (Protocol OMNI specific)
LLAMA_BENCH="${LLAMA_BENCH:-/opt/llama.cpp-mxfp4/build/bin/llama-bench}"
DEFAULT_MODEL="/nvme/models/deepseek-r1-0528-q4km/deepseek-ai_DeepSeek-R1-0528-Q4_K_M/deepseek-ai_DeepSeek-R1-0528-Q4_K_M-00001-of-00011.gguf"

# Alternative models for quick testing
QWEN_CODER_MODEL="/nvme/models/qwen2.5-coder-32b/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf"
DEEPSEEK_R1_MODEL="/nvme/models/deepseek-r1/DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00001-of-00009.gguf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Sanitize nvidia-smi value: convert N/A or empty to null, strip whitespace
sanitize_value() {
    local val="$1"
    val="${val#"${val%%[![:space:]]*}"}"  # trim leading
    val="${val%"${val##*[![:space:]]}"}"  # trim trailing
    if [[ -z "$val" || "$val" == *"N/A"* || "$val" == "[Not Supported]" ]]; then
        echo "null"
    else
        echo "$val"
    fi
}

# JSON-escape a string (handles quotes, backslashes, and all control chars U+0000-U+001F)
json_escape() {
    local str="$1"
    local result
    # If jq is available, use it for proper escaping
    if command -v jq &>/dev/null; then
        # jq -Rs reads raw input as single string, outputs JSON-encoded with quotes
        # Strip outer quotes with sed; check jq exit status explicitly
        result=$(printf '%s' "$str" | jq -Rs '.' 2>/dev/null)
        if [[ $? -eq 0 && -n "$result" ]]; then
            # Strip leading/trailing quotes from jq output
            result="${result#\"}"
            result="${result%\"}"
            printf '%s' "$result"
            return
        fi
        # jq failed, fall through to manual escaping
    fi
    # Manual escaping fallback
    str="${str//\\/\\\\}"  # escape backslashes first
    str="${str//\"/\\\"}"  # escape quotes
    # Escape all control characters explicitly
    str="${str//$'\x00'/\\u0000}"
    str="${str//$'\x01'/\\u0001}"
    str="${str//$'\x02'/\\u0002}"
    str="${str//$'\x03'/\\u0003}"
    str="${str//$'\x04'/\\u0004}"
    str="${str//$'\x05'/\\u0005}"
    str="${str//$'\x06'/\\u0006}"
    str="${str//$'\x07'/\\u0007}"
    str="${str//$'\x08'/\\b}"      # backspace
    str="${str//$'\x09'/\\t}"      # tab
    str="${str//$'\x0A'/\\n}"      # newline
    str="${str//$'\x0B'/\\u000B}"  # vertical tab
    str="${str//$'\x0C'/\\f}"      # form feed
    str="${str//$'\x0D'/\\r}"      # carriage return
    str="${str//$'\x0E'/\\u000E}"
    str="${str//$'\x0F'/\\u000F}"
    str="${str//$'\x10'/\\u0010}"
    str="${str//$'\x11'/\\u0011}"
    str="${str//$'\x12'/\\u0012}"
    str="${str//$'\x13'/\\u0013}"
    str="${str//$'\x14'/\\u0014}"
    str="${str//$'\x15'/\\u0015}"
    str="${str//$'\x16'/\\u0016}"
    str="${str//$'\x17'/\\u0017}"
    str="${str//$'\x18'/\\u0018}"
    str="${str//$'\x19'/\\u0019}"
    str="${str//$'\x1A'/\\u001A}"
    str="${str//$'\x1B'/\\u001B}"
    str="${str//$'\x1C'/\\u001C}"
    str="${str//$'\x1D'/\\u001D}"
    str="${str//$'\x1E'/\\u001E}"
    str="${str//$'\x1F'/\\u001F}"
    printf '%s' "$str"
}

# GPU telemetry capture - outputs proper JSONL (one JSON object per line)
capture_gpu_state() {
    local phase="$1"
    local output_file="$2"
    local ts
    ts="$(date -Iseconds)"
    
    nvidia-smi --query-gpu=index,name,temperature.gpu,power.draw,memory.used,memory.total,clocks.gr,clocks.mem,ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total \
        --format=csv,noheader,nounits 2>/dev/null | while IFS=',' read -r idx name temp power mem_used mem_total clk_gr clk_mem ecc_corr ecc_uncorr; do
        # Sanitize all values
        idx=$(sanitize_value "$idx")
        name="${name#"${name%%[![:space:]]*}"}"
        name="${name%"${name##*[![:space:]]}"}"
        name=$(json_escape "$name")  # JSON-escape the GPU name
        temp=$(sanitize_value "$temp")
        power=$(sanitize_value "$power")
        mem_used=$(sanitize_value "$mem_used")
        mem_total=$(sanitize_value "$mem_total")
        clk_gr=$(sanitize_value "$clk_gr")
        clk_mem=$(sanitize_value "$clk_mem")
        ecc_corr=$(sanitize_value "$ecc_corr")
        ecc_uncorr=$(sanitize_value "$ecc_uncorr")
        
        # Output as single-line JSONL
        printf '{"phase":"%s","timestamp":"%s","gpu_index":%s,"gpu_name":"%s","temperature_c":%s,"power_w":%s,"memory_used_mb":%s,"memory_total_mb":%s,"clock_graphics_mhz":%s,"clock_memory_mhz":%s,"ecc_corrected":%s,"ecc_uncorrected":%s}\n' \
            "$phase" "$ts" "$idx" "$name" "$temp" "$power" "$mem_used" "$mem_total" "$clk_gr" "$clk_mem" "$ecc_corr" "$ecc_uncorr" >> "$output_file"
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ ! -x "$LLAMA_BENCH" ]]; then
        log_error "llama-bench not found at: $LLAMA_BENCH"
        log_info "Set LLAMA_BENCH env var or install llama.cpp"
        exit 1
    fi
    
    if ! command -v nvidia-smi &>/dev/null; then
        log_warn "nvidia-smi not found - GPU telemetry disabled"
        GPU_TELEMETRY=false
    else
        GPU_TELEMETRY=true
    fi
    
    if ! command -v jq &>/dev/null; then
        log_warn "jq not found - JSON processing limited"
    fi
    
    log_success "Prerequisites OK"
}

# Define sweep presets
get_preset_params() {
    local preset="$1"
    
    case "$preset" in
        quick)
            # Quick sanity check (~5 min)
            NGL_VALUES="10"
            BATCH_VALUES="2048"
            UBATCH_VALUES="512"
            FA_VALUES="0,1"
            CTK_VALUES="f16,q4_1"
            SPLIT_MODE="none"
            TENSOR_SPLIT_LIST=()  # No tensor split sweeping
            REPETITIONS=2
            ;;
        full)
            # Complete GPU parameter sweep (~30 min)
            NGL_VALUES="5,10,15,20"
            BATCH_VALUES="512,1024,2048,4096"
            UBATCH_VALUES="256,512,1024"
            FA_VALUES="0,1"
            CTK_VALUES="f16,q8_0,q4_1,q4_0"
            SPLIT_MODE="none,layer"
            TENSOR_SPLIT_LIST=()  # No tensor split sweeping (see S-021)
            REPETITIONS=3
            ;;
        kv)
            # KV cache type comparison only
            NGL_VALUES="10"
            BATCH_VALUES="2048"
            UBATCH_VALUES="512"
            FA_VALUES="1"
            CTK_VALUES="f16,q8_0,q4_1,q4_0"
            SPLIT_MODE="none"
            TENSOR_SPLIT_LIST=()
            REPETITIONS=5
            ;;
        ngl)
            # GPU layer offload sweep
            NGL_VALUES="1,5,10,15,20,25,30"
            BATCH_VALUES="2048"
            UBATCH_VALUES="512"
            FA_VALUES="1"
            CTK_VALUES="q4_1"
            SPLIT_MODE="none"
            TENSOR_SPLIT_LIST=()
            REPETITIONS=3
            ;;
        batch)
            # Batch size optimization
            NGL_VALUES="10"
            BATCH_VALUES="256,512,1024,2048,4096,8192"
            UBATCH_VALUES="128,256,512,1024"
            FA_VALUES="1"
            CTK_VALUES="q4_1"
            SPLIT_MODE="none"
            TENSOR_SPLIT_LIST=()
            REPETITIONS=3
            ;;
        multigpu)
            # Multi-GPU tensor split comparison (VERIFICATION ONLY)
            # S-021 already showed: tensor-split 75,25 = 8.26 tok/s vs single = 11.74 tok/s (-30%)
            log_warn "=============================================="
            log_warn "TENSOR SPLIT VERIFICATION MODE"
            log_warn "S-021 results: tensor-split = -30% SLOWER"
            log_warn "This preset verifies that finding; NOT for production"
            log_warn "=============================================="
            NGL_VALUES="10"
            BATCH_VALUES="2048"
            UBATCH_VALUES="512"
            FA_VALUES="1"
            CTK_VALUES="q4_1"
            SPLIT_MODE="none"
            # Tensor split values: semicolon-separated, each value is comma-separated GPU weights
            # Empty string = no tensor split (single GPU), "75,25" = 75% GPU0 / 25% GPU1
            TENSOR_SPLIT_LIST=("" "75,25" "65,35" "50,50")
            REPETITIONS=3
            ;;
        custom)
            # Use environment variables
            NGL_VALUES="${SWEEP_NGL:-10}"
            BATCH_VALUES="${SWEEP_BATCH:-2048}"
            UBATCH_VALUES="${SWEEP_UBATCH:-512}"
            FA_VALUES="${SWEEP_FA:-0,1}"
            CTK_VALUES="${SWEEP_CTK:-f16,q4_1}"
            SPLIT_MODE="${SWEEP_SM:-none}"
            # SWEEP_TS: semicolon-separated tensor split values, e.g., ";75,25;65,35"
            # Empty segments mean no tensor split
            if [[ -n "${SWEEP_TS:-}" ]]; then
                IFS=';' read -ra TENSOR_SPLIT_LIST <<< "$SWEEP_TS"
            else
                TENSOR_SPLIT_LIST=()
            fi
            REPETITIONS="${SWEEP_REPS:-3}"
            ;;
        *)
            log_error "Unknown preset: $preset"
            echo "Available presets: quick, full, kv, ngl, batch, multigpu, custom"
            exit 1
            ;;
    esac
}

# Run a single llama-bench invocation
run_single_bench() {
    local model_path="$1"
    local tensor_split="$2"
    local results_file="$3"
    local bench_log="$4"
    
    # Build llama-bench command as array (safer than eval)
    local -a cmd_args=(
        "$LLAMA_BENCH"
        -m "$model_path"
        -ngl "$NGL_VALUES"
        -b "$BATCH_VALUES"
        -ub "$UBATCH_VALUES"
        -fa "$FA_VALUES"
        -ctk "$CTK_VALUES"
        -sm "$SPLIT_MODE"
        -r "$REPETITIONS"
        -p 512
        -n 128
        -o json
        --progress
    )
    
    # Add tensor split if specified
    if [[ -n "$tensor_split" ]]; then
        cmd_args+=(-ts "$tensor_split")
    fi
    
    log_info "Running: ${cmd_args[*]}"
    
    # Run benchmark: --progress outputs to stderr, stdout is JSON
    # Write to results_file (not append), append to bench_log
    if "${cmd_args[@]}" > "$results_file" 2>>"$bench_log"; then
        return 0
    else
        return 1
    fi
}

# Run the benchmark sweep
run_sweep() {
    local model_path="$1"
    local results_file="$OUTPUT_DIR/llama-bench-results.json"
    local gpu_log="$OUTPUT_DIR/gpu-telemetry.jsonl"
    local bench_log="$OUTPUT_DIR/llama-bench.log"
    
    mkdir -p "$OUTPUT_DIR"
    
    # Create temp directory for intermediate results
    local temp_dir
    temp_dir=$(mktemp -d)
    
    log_info "Starting benchmark sweep"
    log_info "  Model: $model_path"
    log_info "  Output: $OUTPUT_DIR"
    log_info "  Parameters:"
    log_info "    -ngl: $NGL_VALUES"
    log_info "    -b:   $BATCH_VALUES"
    log_info "    -ub:  $UBATCH_VALUES"
    log_info "    -fa:  $FA_VALUES"
    log_info "    -ctk: $CTK_VALUES"
    log_info "    -sm:  $SPLIT_MODE"
    if [[ ${#TENSOR_SPLIT_LIST[@]} -gt 0 ]]; then
        log_info "    -ts:  ${TENSOR_SPLIT_LIST[*]}"
    fi
    log_info "    -r:   $REPETITIONS"
    
    # Save configuration
    # Store raw SWEEP_TS for jq-free fallback (with JSON escaping)
    local ts_raw="${SWEEP_TS:-}"
    local ts_raw_escaped
    ts_raw_escaped=$(json_escape "$ts_raw")
    
    local ts_json="[]"
    if [[ ${#TENSOR_SPLIT_LIST[@]} -gt 0 ]]; then
        if command -v jq &>/dev/null; then
            ts_json=$(printf '%s\n' "${TENSOR_SPLIT_LIST[@]}" | jq -R . | jq -s . 2>/dev/null || echo "[]")
        else
            # Manual JSON array construction without jq (use json_escape helper)
            ts_json="["
            local first=true
            for ts in "${TENSOR_SPLIT_LIST[@]}"; do
                local escaped_ts
                escaped_ts=$(json_escape "$ts")
                if [[ "$first" == "true" ]]; then
                    ts_json+="\"$escaped_ts\""
                    first=false
                else
                    ts_json+=",\"$escaped_ts\""
                fi
            done
            ts_json+="]"
        fi
    fi
    
    cat > "$OUTPUT_DIR/config.json" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "model_path": "$model_path",
  "llama_bench_path": "$LLAMA_BENCH",
  "preset": "${PRESET:-custom}",
  "sweep_ts_raw": "$ts_raw_escaped",
  "parameters": {
    "ngl": "$NGL_VALUES",
    "batch": "$BATCH_VALUES",
    "ubatch": "$UBATCH_VALUES",
    "flash_attn": "$FA_VALUES",
    "cache_type_k": "$CTK_VALUES",
    "split_mode": "$SPLIT_MODE",
    "tensor_split_list": $ts_json,
    "repetitions": $REPETITIONS
  }
}
EOF
    
    # Capture pre-benchmark GPU state
    if [[ "$GPU_TELEMETRY" == "true" ]]; then
        log_info "Capturing pre-benchmark GPU state..."
        capture_gpu_state "pre" "$gpu_log"
    fi
    
    local start_time end_time duration
    start_time=$(date +%s)
    local run_count=0
    
    # If no tensor split list, run once without -ts
    if [[ ${#TENSOR_SPLIT_LIST[@]} -eq 0 ]]; then
        TENSOR_SPLIT_LIST=("")
    fi
    
    # Run benchmarks for each tensor split configuration
    for ts in "${TENSOR_SPLIT_LIST[@]}"; do
        local ts_desc="${ts:-single-gpu}"
        log_info "=== Tensor split: $ts_desc ==="
        
        local run_result="$temp_dir/run_${run_count}.json"
        
        if run_single_bench "$model_path" "$ts" "$run_result" "$bench_log"; then
            if [[ -s "$run_result" ]]; then
                ((run_count++))
            fi
        else
            log_warn "Benchmark failed for tensor_split=$ts_desc (see $bench_log)"
        fi
    done
    
    # Merge all JSON results using jq (or manual merge if jq unavailable)
    if [[ $run_count -gt 0 ]]; then
        log_info "Merging $run_count result files..."
        local merge_success=false
        
        if command -v jq &>/dev/null; then
            # Use jq to concatenate all JSON arrays into one
            if jq -s 'add' "$temp_dir"/run_*.json > "$results_file" 2>/dev/null; then
                merge_success=true
            else
                log_warn "jq merge failed, falling back to manual merge"
            fi
        fi
        
        if [[ "$merge_success" != "true" ]]; then
            # Manual JSON array merge without jq (or as fallback)
            [[ -z "$(command -v jq)" ]] && log_warn "jq not found - using manual JSON merge"
            echo "[" > "$results_file"
            local first_file=true
            for f in "$temp_dir"/run_*.json; do
                [[ -s "$f" ]] || continue
                # Strip outer brackets with whitespace tolerance
                local content
                content=$(sed -E 's/^[[:space:]]*\[//; s/\][[:space:]]*$//' "$f" | sed '/^[[:space:]]*$/d')
                if [[ -n "$content" ]]; then
                    if [[ "$first_file" == "true" ]]; then
                        echo "$content" >> "$results_file"
                        first_file=false
                    else
                        echo ",$content" >> "$results_file"
                    fi
                fi
            done
            echo "]" >> "$results_file"
        fi
    else
        echo "[]" > "$results_file"
    fi
    
    # Cleanup temp directory
    rm -rf "$temp_dir"
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [[ $run_count -gt 0 ]]; then
        log_success "Completed $run_count benchmark run(s) in ${duration}s"
    else
        log_error "All benchmark runs failed. Check $bench_log"
        exit 1
    fi
    
    # Capture post-benchmark GPU state
    if [[ "$GPU_TELEMETRY" == "true" ]]; then
        log_info "Capturing post-benchmark GPU state..."
        capture_gpu_state "post" "$gpu_log"
    fi
    
    # Generate summary
    generate_summary "$results_file" "$OUTPUT_DIR/summary.md"
}

# Generate human-readable summary
generate_summary() {
    local results_file="$1"
    local summary_file="$2"
    
    log_info "Generating summary..."
    
    # Check if any non-empty tensor split values exist
    local ts_display="N/A (single GPU)"
    local has_tensor_split=false
    for ts in "${TENSOR_SPLIT_LIST[@]}"; do
        if [[ -n "$ts" ]]; then
            has_tensor_split=true
            break
        fi
    done
    if [[ "$has_tensor_split" == "true" ]]; then
        ts_display="${TENSOR_SPLIT_LIST[*]}"
    fi
    
    cat > "$summary_file" <<EOF
# Benchmark Sweep Results

**Date**: $TIMESTAMP
**Model**: $(basename "$MODEL_PATH")

## Configuration

| Parameter | Values |
|-----------|--------|
| GPU Layers (ngl) | $NGL_VALUES |
| Batch Size | $BATCH_VALUES |
| Micro-batch | $UBATCH_VALUES |
| Flash Attention | $FA_VALUES |
| KV Cache Type | $CTK_VALUES |
| Split Mode | $SPLIT_MODE |
| Tensor Split | $ts_display |
| Repetitions | $REPETITIONS |

## Results Summary

EOF

    # Parse JSON results if jq available
    if command -v jq &>/dev/null && [[ -f "$results_file" ]]; then
        # Separate prompt eval and generation results
        echo "### Token Generation Results" >> "$summary_file"
        echo "" >> "$summary_file"
        echo "| ngl | batch | ubatch | flash | cache_k | tensor_split | tok/s | stddev |" >> "$summary_file"
        echo "|-----|-------|--------|-------|---------|--------------|-------|--------|" >> "$summary_file"
        
        jq -r '
            [.[] | select(.n_gen > 0)] | 
            sort_by(-.avg_ts) | 
            .[:15] | 
            .[] | 
            "| \(.n_gpu_layers) | \(.n_batch) | \(.n_ubatch) | \(.flash_attn) | \(.type_k) | " + (if .tensor_split then (.tensor_split | tostring) else "none" end) + " | \(.avg_ts | . * 100 | round / 100) | \(.stddev_ts | . * 100 | round / 100) |"
        ' "$results_file" 2>/dev/null >> "$summary_file" || true
        
        echo "" >> "$summary_file"
        echo "### Prompt Processing Results" >> "$summary_file"
        echo "" >> "$summary_file"
        echo "| ngl | batch | ubatch | flash | cache_k | tensor_split | tok/s | stddev |" >> "$summary_file"
        echo "|-----|-------|--------|-------|---------|--------------|-------|--------|" >> "$summary_file"
        
        jq -r '
            [.[] | select(.n_prompt > 0 and .n_gen == 0)] | 
            sort_by(-.avg_ts) | 
            .[:15] | 
            .[] | 
            "| \(.n_gpu_layers) | \(.n_batch) | \(.n_ubatch) | \(.flash_attn) | \(.type_k) | " + (if .tensor_split then (.tensor_split | tostring) else "none" end) + " | \(.avg_ts | . * 100 | round / 100) | \(.stddev_ts | . * 100 | round / 100) |"
        ' "$results_file" 2>/dev/null >> "$summary_file" || true
        
        echo "" >> "$summary_file"
        echo "### Best Configuration (Generation)" >> "$summary_file"
        echo "" >> "$summary_file"
        
        jq -r '
            [.[] | select(.n_gen > 0)] | 
            sort_by(-.avg_ts) | 
            .[0] // empty | 
            "- **GPU Layers**: \(.n_gpu_layers)\n- **Batch Size**: \(.n_batch)\n- **Micro-batch**: \(.n_ubatch)\n- **Flash Attention**: \(.flash_attn)\n- **KV Cache Type**: \(.type_k)\n- **Tensor Split**: " + (if .tensor_split then (.tensor_split | tostring) else "none (single GPU)" end) + "\n- **Token Generation**: \(.avg_ts | . * 100 | round / 100) tok/s (± \(.stddev_ts | . * 100 | round / 100))"
        ' "$results_file" 2>/dev/null >> "$summary_file" || true
    else
        echo "*Install jq for detailed analysis*" >> "$summary_file"
    fi
    
    echo "" >> "$summary_file"
    echo "## Files" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "- \`llama-bench-results.json\` - Raw benchmark data" >> "$summary_file"
    echo "- \`llama-bench.log\` - Benchmark stderr/progress output" >> "$summary_file"
    echo "- \`gpu-telemetry.jsonl\` - GPU state snapshots (JSONL format)" >> "$summary_file"
    echo "- \`config.json\` - Sweep configuration" >> "$summary_file"
    
    log_success "Summary saved to: $summary_file"
}

# Find optimal configuration from results
find_optimal() {
    local results_file="$1"
    
    if ! command -v jq &>/dev/null; then
        log_warn "jq required for optimal config analysis"
        return
    fi
    
    echo ""
    log_info "=== Optimal Configuration ==="
    
    local result
    result=$(jq -r '
        [.[] | select(.n_gen > 0)] | 
        sort_by(-.avg_ts) | 
        .[0] // empty | 
        "Token Generation: \(.avg_ts | . * 100 | round / 100) tok/s\n" +
        "  -ngl \(.n_gpu_layers)\n" +
        "  -b \(.n_batch)\n" +
        "  -ub \(.n_ubatch)\n" +
        "  -fa \(.flash_attn)\n" +
        "  -ctk \(.type_k)\n" +
        "  -sm \(.split_mode)\n" +
        "  -ts \(if .tensor_split then .tensor_split else \"none\" end)"
    ' "$results_file" 2>/dev/null)
    
    if [[ -n "$result" ]]; then
        echo "$result"
        
        # Warn if tensor split is in optimal config (shouldn't be for Protocol OMNI)
        if echo "$result" | grep -q "ts.*[0-9]"; then
            echo ""
            log_warn "Optimal config uses tensor split - verify against S-021 findings"
            log_warn "S-021: tensor-split 75,25 = 8.26 tok/s vs single GPU = 11.74 tok/s"
        fi
    else
        log_warn "Could not parse results"
    fi
}

# Main entry point
main() {
    local preset="${1:-quick}"
    local model_override="${2:-}"
    
    echo "=========================================="
    echo " Protocol OMNI Benchmark Sweep"
    echo " $(date)"
    echo "=========================================="
    echo ""
    
    check_prerequisites
    
    PRESET="$preset"
    get_preset_params "$preset"
    
    # Model path resolution with explicit error on missing override
    if [[ -n "$model_override" ]]; then
        if [[ -f "$model_override" ]]; then
            MODEL_PATH="$model_override"
        else
            log_error "Specified model not found: $model_override"
            exit 1
        fi
    elif [[ -f "$DEFAULT_MODEL" ]]; then
        MODEL_PATH="$DEFAULT_MODEL"
    else
        log_error "Default model not found. Specify path: $0 $preset /path/to/model.gguf"
        exit 1
    fi
    
    run_sweep "$MODEL_PATH"
    find_optimal "$OUTPUT_DIR/llama-bench-results.json"
    
    echo ""
    log_success "Results saved to: $OUTPUT_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Review: cat $OUTPUT_DIR/summary.md"
    echo "  2. Apply optimal config to llama-server"
    echo "  3. Re-run production benchmark"
}

# Help message
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<EOF
Protocol OMNI Benchmark Sweep

Usage: $0 [preset] [model_path]

Presets:
  quick     Quick sanity check (~5 min, limited combinations)
  full      Complete GPU parameter sweep (~30 min)
  kv        KV cache type comparison only
  ngl       GPU layer offload sweep
  batch     Batch size optimization
  multigpu  Multi-GPU tensor split VERIFICATION (see S-021: -30% slower)
  custom    Use SWEEP_* environment variables

Environment Variables (for custom preset):
  SWEEP_NGL     GPU layers (default: 10)
  SWEEP_BATCH   Batch sizes (default: 2048)
  SWEEP_UBATCH  Micro-batch sizes (default: 512)
  SWEEP_FA      Flash attention (default: 0,1)
  SWEEP_CTK     KV cache types (default: f16,q4_1)
  SWEEP_SM      Split mode (default: none)
  SWEEP_TS      Tensor split values, semicolon-separated (e.g., ";75,25;65,35")
                Each value is comma-separated GPU weights. Empty = single GPU.
  SWEEP_REPS    Repetitions (default: 3)
  LLAMA_BENCH   Path to llama-bench binary

Architecture Note (S-021, S-031):
  For asymmetric VRAM (96GB + 32GB), INDEPENDENT WORKLOADS are optimal.
  S-021 tested tensor split: -ts 75,25 = 8.26 tok/s vs single GPU = 11.74 tok/s
  Tensor split is 30% SLOWER due to PCIe overhead. Do NOT use in production.
  The 'multigpu' preset is for verification benchmarking only.

Examples:
  $0 quick                                    # Quick 5-minute sweep
  $0 full                                     # Full 30-minute sweep  
  $0 kv /path/to/model.gguf                   # KV cache comparison
  SWEEP_NGL=5,10,15 $0 custom                 # Custom sweep
  SWEEP_TS=";75,25;65,35" $0 custom           # Test tensor splits
  $0 multigpu                                 # Verify S-021 findings

Output:
  benchmarks/YYYY-MM-DD_HHMMSS-sweep/
    ├── llama-bench-results.json     # Raw benchmark data (JSON array)
    ├── llama-bench.log              # Benchmark stderr/progress
    ├── gpu-telemetry.jsonl          # GPU state snapshots (JSONL)
    ├── config.json                  # Sweep configuration
    └── summary.md                   # Human-readable summary
EOF
    exit 0
fi

main "$@"
