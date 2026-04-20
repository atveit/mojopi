#!/usr/bin/env bash
# fetch_model.sh — download an MLX model via mlx-lm with preflight + progress.
#
# Usage:
#   scripts/fetch_model.sh gemma-4-e4b-it-4bit                # short name (mlx-community/)
#   scripts/fetch_model.sh mlx-community/Qwen3-0.6B-4bit      # full repo id
#
# Exit codes:
#   0 — downloaded successfully
#   1 — download failed
#   2 — not enough disk space
#   3 — model already cached (not an error; just informational)

set -euo pipefail

MODEL_ARG="${1:-}"
if [ -z "$MODEL_ARG" ]; then
    echo "usage: fetch_model.sh <short-name-or-full-repo>"
    echo ""
    echo "Examples:"
    echo "  scripts/fetch_model.sh gemma-4-e4b-it-4bit"
    echo "  scripts/fetch_model.sh mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
    exit 1
fi

# Expand short name to mlx-community/ prefix if no / in arg
if [[ "$MODEL_ARG" != */* ]]; then
    MODEL_REPO="mlx-community/$MODEL_ARG"
else
    MODEL_REPO="$MODEL_ARG"
fi

HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}/hub"
SLUG="models--${MODEL_REPO//\//--}"
MODEL_DIR="$HF_CACHE/$SLUG"

# If already cached, exit 3 (informational)
if [ -d "$MODEL_DIR" ]; then
    SIZE=$(du -sh "$MODEL_DIR" 2>/dev/null | awk '{print $1}')
    echo "already cached: $MODEL_REPO  ($SIZE)"
    exit 3
fi

# Disk preflight: need roughly 5 GB free for a 4-bit 8B model, less for smaller.
# Use a conservative 6 GB threshold.
FREE_MB=$(df -m "$HOME" | awk 'NR==2 {print $4}')
NEEDED_MB=6000
if [ "$FREE_MB" -lt "$NEEDED_MB" ]; then
    echo "error: only ${FREE_MB} MB free in \$HOME; need at least ${NEEDED_MB} MB" >&2
    exit 2
fi

echo "downloading $MODEL_REPO ..."
echo "  destination: $MODEL_DIR"
echo "  free disk:   ${FREE_MB} MB"
echo ""

PIXI_BIN="${PIXI_BIN:-$HOME/.pixi/bin/pixi}"
"$PIXI_BIN" run python -c "
from mlx_lm import load
import time, sys
t0 = time.time()
print('loading model — mlx-lm will resolve + download weights...')
try:
    load('$MODEL_REPO')
except Exception as e:
    print(f'error: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
elapsed = time.time() - t0
print(f'done in {elapsed:.1f}s')
"

echo ""
FINAL_SIZE=$(du -sh "$MODEL_DIR" 2>/dev/null | awk '{print $1}')
echo "cached: $MODEL_REPO  ($FINAL_SIZE)"
