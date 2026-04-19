#!/usr/bin/env bash
# Invoke the mojopi binary with the correct import paths.
# `-I src` so prompt/formatter and max_brain/inference resolve in Mojo.
# PYTHONPATH so max_brain.pipeline resolves when Mojo calls Python.import_module.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH="src:${PYTHONPATH:-}" exec mojo run -I src src/main.mojo -- "$@"
