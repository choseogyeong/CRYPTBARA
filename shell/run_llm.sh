#!/bin/bash

# Parse --target=, --experiment=, --session=
SINGLE_TARGET=""
SESSION_TAG="${SESSION_TAG:-}"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --target=*)      SINGLE_TARGET="${1#*=}";;
        --experiment=*)  EXPERIMENT_KEY="${1#*=}";;
        --session=*)     SESSION_TAG="${1#*=}";;
        *) echo "Unknown option: $1"; exit 1;;
    esac
    shift
done

if [[ -z "$SESSION_TAG" ]]; then
    SESSION_TAG=$(date +%Y%m%d_%H%M%S)
fi
echo "[DEBUG] SESSION_TAG = $SESSION_TAG"

PROJECT_DIR=$(pwd)
OUTPUT_BASE="$PROJECT_DIR/run_results/${SESSION_TAG}/outputs"
LLM_OUTPUT_BASE="$PROJECT_DIR/run_results/${SESSION_TAG}/outputs_llm"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/llm_experiments_${SESSION_TAG}.log"


if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "[!] OPENAI_API_KEY is not set. Please export your key before running this script." | tee -a "$LOG_FILE"
    exit 1
fi

mkdir -p "$OUTPUT_BASE" "$LLM_OUTPUT_BASE" "$LOG_DIR"

echo "[*] LLM experiment log started at $(date)" > "$LOG_FILE"

# Template and rule checks
for template in C1.txt; do
    if [ ! -f "$PROJECT_DIR/llm/templates/$template" ]; then
        echo "[!] Warning: Missing template $template" | tee -a "$LOG_FILE"
    fi
done

if [ ! -f "$PROJECT_DIR/llm/rules/rules.json" ]; then
    echo "[!] Warning: rules.json is missing" | tee -a "$LOG_FILE"
fi

# Target selection
if [[ -n "$SINGLE_TARGET" ]]; then
    targets=("${OUTPUT_BASE}/$SINGLE_TARGET/merged_results.json")
else
    targets=(${OUTPUT_BASE}/*/merged_results.json)
fi

echo "[+] Starting LLM experiments for selected targets..." | tee -a "$LOG_FILE"
echo "[+] Target files: ${#targets[@]}" | tee -a "$LOG_FILE"
echo "[+] Experiment key: $EXPERIMENT_KEY" | tee -a "$LOG_FILE"
echo "[+] API Key prefix: ${OPENAI_API_KEY:0:4}...${OPENAI_API_KEY: -4}" | tee -a "$LOG_FILE"

total=${#targets[@]}
current=0

for merged_file in "${targets[@]}"; do
    ((current++))
    percent=$((current * 100 / total))
    echo -e "\n[*] [$percent%] Processing: $merged_file" | tee -a "$LOG_FILE"

    target_name=$(basename "$(dirname "$merged_file")")

    if [[ ! -f "$merged_file" ]]; then
        echo "[!] Skipping invalid target: $merged_file" | tee -a "$LOG_FILE"
        continue
    fi

    file_content=$(tr -d '[:space:]' < "$merged_file")
    if [[ "$file_content" == "{}" ]]; then
        echo "[!] Skipping empty result: $merged_file" | tee -a "$LOG_FILE"
        continue
    fi

    cmd="PYTHONPATH=$PROJECT_DIR python3 $PROJECT_DIR/llm/run_llm_experiments.py \"$target_name\" \"$EXPERIMENT_KEY\" \"$SESSION_TAG\""
    echo "[*] Running: $cmd" | tee -a "$LOG_FILE"

    if eval "$cmd"; then
        llm_result_file="$LLM_OUTPUT_BASE/$target_name/C1/llm_results.json"
        if [[ -f "$llm_result_file" ]]; then
            echo "[✓] Success — Result found: $llm_result_file" | tee -a "$LOG_FILE"
            grep -q "error" "$llm_result_file" && echo "[!] Warning: Error found in result" | tee -a "$LOG_FILE"
        else
            echo "[✗] Failure — No result found for C1" | tee -a "$LOG_FILE"
        fi
    else
        echo "[✗] Execution failed for $target_name" | tee -a "$LOG_FILE"
    fi
done

echo -e "\n[✓] All LLM experiments finished." | tee -a "$LOG_FILE"
