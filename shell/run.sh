#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

mkdir -p logs

# Generate a session tag based on the current timestamp
export SESSION_TAG=$(date +%Y%m%d_%H%M%S)
ALL_ARGS="$@"

echo "[*] Session Tag: $SESSION_TAG"
echo "[*] Starting full pipeline..."

# 1. Run static analysis
bash ./shell/run_all.sh $ALL_ARGS

# 2. Run LLM-based detection
bash ./shell/run_llm.sh $ALL_ARGS

# 3. Summarize results
echo "[✓] Done. Generating summary..."
python3 ./utils/result.py --session="$SESSION_TAG"
