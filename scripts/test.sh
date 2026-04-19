#!/usr/bin/env bash
# Run full test suite: Mojo tests + Python tests. Invoked by `pixi run test`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Mojo tests"
mojo test tests/

echo "==> Python tests"
PYTHONPATH="src:${PYTHONPATH:-}" pytest tests/ -v

echo "All tests passed."
