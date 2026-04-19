#!/usr/bin/env bash
# mojopi launcher — invoked when installed via pixi global / conda
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOJOPI_DIR="$(dirname "$SCRIPT_DIR")/lib/mojopi"

if [ -d "$MOJOPI_DIR/src" ]; then
    PYTHONPATH="$MOJOPI_DIR/src" exec mojo run -I "$MOJOPI_DIR/src" "$MOJOPI_DIR/src/main.mojo" -- "$@"
else
    # Development mode: run from repo root
    REPO_DIR="$(dirname "$SCRIPT_DIR")"
    PYTHONPATH="$REPO_DIR/src" exec mojo run -I "$REPO_DIR/src" "$REPO_DIR/src/main.mojo" -- "$@"
fi
