#!/usr/bin/env bash
# Verify Mojo source is formatted. Invoked by `pixi run format-check`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mojo format --check src/ tests/
