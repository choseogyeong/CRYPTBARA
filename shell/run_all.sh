#!/bin/bash

mkdir -p logs
RUN_ID=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/run_all_${RUN_ID}.log"

# Define and export SESSION_TAG
SESSION_TAG=${SESSION_TAG:-$(date +%Y%m%d_%H%M%S)}
export SESSION_TAG=$RUN_ID
OUTPUT_BASE="run_results/${SESSION_TAG}/outputs"

echo "[*] Static analysis started at $(date)" | tee -a "$LOG_FILE"

# 1. Clean up previous flattened files
echo "[+] Cleaning up old files in 'target/'..."
rm -f target/*.py

TARGET_SOURCE="target_files"
TARGET_FLAT="target"
JOERN_SCRIPT="scripts/run_joern_script.py"
FORMATTER_SCRIPT="scripts/JoernUnifiedParser.py"
AST_SCRIPT="scripts/ast_interflow.py"
MERGE_SCRIPT="scripts/merge.py"
TREE_SCRIPT="scripts/generate_call_tree.py"
FLATTENER_SCRIPT="utils/process_filename.py"

DATA="target_files"  # Default data source

# Parse CLI options (LLM-related flags are ignored)
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --file=*) SINGLE_FILE="${1#*=}";;
        --list=*) FILE_LIST="${1#*=}";;
        --output=*) OUTPUT_BASE="${1#*=}";;
        --data=*) DATA="${1#*=}";;
        --target=*|--experiment=*|--session=*) 
            ;;  # Ignore LLM-specific options
        *) 
            echo "Unknown option: $1" | tee -a "$LOG_FILE"
            echo "Valid options: --file=, --list=, --output=, --data=" | tee -a "$LOG_FILE"
            exit 1
            ;;
    esac
    shift
done

# Flatten if directory provided
if [[ -f "$DATA" ]]; then
    FILES=("$DATA")
elif [[ -d "$DATA" ]]; then
    python3 "$FLATTENER_SCRIPT" "$DATA" >> "$LOG_FILE" 2>&1
    FILES=($TARGET_FLAT/*.py)
else
    echo "[!] Invalid path: $DATA" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[+] Beginning analysis..." | tee -a "$LOG_FILE"

# Progress bar
print_progress() {
    local current=$1
    local total=$2
    local width=50
    local progress=$((current * width / total))
    local percent=$((current * 100 / total))
    local bar=$(printf "%-${width}s" "#" | sed "s/ /-/g")
    printf "\r[%-${width}s] %3d%% Completed" "${bar:0:progress}" "$percent"
}

# Process all target files
total=${#FILES[@]}
current=0

for file_path in "${FILES[@]}"; do
    ((current++))
    print_progress "$current" "$total"

    file_name=$(basename "$file_path")
    target_name="${file_name%.*}"

    mkdir -p "$OUTPUT_BASE/$target_name/joern"
    mkdir -p "$OUTPUT_BASE/$target_name/ast"

    echo -e "\n[*] Processing $target_name..." | tee -a "$LOG_FILE"

    echo "[→] Running Joern..." | tee -a "$LOG_FILE"
    python3 "$JOERN_SCRIPT" "$file_path" "$target_name" "$SESSION_TAG" >> "$LOG_FILE" 2>&1
    echo "[✓] Joern completed"

    echo "[→] Formatting Joern result..."
    python3 "$FORMATTER_SCRIPT" "$target_name" >> "$LOG_FILE" 2>&1
    echo "[✓] Formatting completed"

    echo "[→] Running AST interprocedural analysis..."
    python3 "$AST_SCRIPT" "$file_path" "$target_name" >> "$LOG_FILE" 2>&1
    echo "[✓] AST analysis completed"

    echo "[→] Merging results..."
    python3 "$MERGE_SCRIPT" "$target_name" >> "$LOG_FILE" 2>&1
    echo "[✓] Merging completed"

    echo "[→] Generating call chain..."
    python3 "$TREE_SCRIPT" "$target_name" >> "$LOG_FILE" 2>&1
    echo "[✓] Call chain generated"
done

echo -e "\n[✓] Static analysis completed at $(date)" | tee -a "$LOG_FILE"
