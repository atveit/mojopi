#!/usr/bin/env bash
# C1 smoke gate: Mojo binary reaches MAX via Python interop and reports version.
# Must exit 0 even when MAX isn't installed — get_max_version() returns
# "max-not-installed" in that case, which is acceptable for the smoke gate
# (real MAX install is a user-side prerequisite, not a CI concern yet).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH="src:${PYTHONPATH:-}" mojo run -I src scripts/_smoke_driver.mojo
