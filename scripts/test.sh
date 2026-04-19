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
MOJO_COUNT=0
for test_file in tests/test_*.mojo; do
    echo "    running $test_file"
    PYTHONPATH="src:${PYTHONPATH:-}" mojo run -I src "$test_file"
    MOJO_COUNT=$((MOJO_COUNT + 1))
done
echo "    ${MOJO_COUNT} Mojo test file(s) run"

echo ""
echo "==> Python tests"
# Use -m "not slow" to skip tests that load model weights (e.g. test_max_interop.py).
# Run the full suite by default; CI may pass -m "not slow" to skip model-loading tests:
#   PYTHONPATH=src:${PYTHONPATH:-} pytest tests/ -v -m "not slow"
#
# Test files discovered automatically by pytest (all tests/test_*.py):
#   - test_context.py          — context loader unit tests
#   - test_embedded_pipeline.py — MAX pipeline smoke tests
#   - test_max_interop.py      — MAX/Mojo interop (may require model weights)
#   - test_session.py          — session store unit tests
#   - test_w1_integration.py   — W1 integration gate tests (skips missing modules)
#   - any future test_*.py files are picked up automatically

PY_FILES=$(ls tests/test_*.py 2>/dev/null | wc -l | tr -d ' ')
echo "    ${PY_FILES} Python test file(s) discovered"
PYTHONPATH="src:${PYTHONPATH:-}" pytest tests/ -v

echo ""
echo "==> Summary"
echo "    Mojo test files run : ${MOJO_COUNT}"
echo "    Python test files   : ${PY_FILES}"
echo "All tests passed."
