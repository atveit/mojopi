#!/usr/bin/env bash
# Run full test suite: Mojo tests + Python tests. Invoked by `pixi run test`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Mojo tests"
# -I src so `from coding_agent.tools.read import read_text` etc. resolve.
# PYTHONPATH so the Python interop module max_brain.pipeline resolves when
# Mojo tests transitively go through Python.import_module (inference.mojo).
PYTHONPATH="src:${PYTHONPATH:-}" mojo test -I src tests/

echo "==> Python tests"
PYTHONPATH="src:${PYTHONPATH:-}" pytest tests/ -v

echo "All tests passed."
