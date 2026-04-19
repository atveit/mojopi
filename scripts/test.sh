#!/usr/bin/env bash
# Run full test suite: Mojo tests + Python tests. Invoked by `pixi run test`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Mojo tests"
# `mojo test` was removed from this toolchain — we run each test file as a
# normal script. Each test_*.mojo has a `def main() raises:` that invokes
# every test function; a failing assertion raises and exits non-zero, which
# `set -e` catches.
#
# -I src   → so `from coding_agent.tools.read import read_text` etc. resolve.
# PYTHONPATH → so max_brain.pipeline resolves when Mojo tests cross into Python
#              via inference.mojo's Python.import_module call.
for test_file in tests/test_*.mojo; do
    echo "    running $test_file"
    PYTHONPATH="src:${PYTHONPATH:-}" mojo run -I src "$test_file"
done

echo "==> Python tests"
PYTHONPATH="src:${PYTHONPATH:-}" pytest tests/ -v

echo "All tests passed."
