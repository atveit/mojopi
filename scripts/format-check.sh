#!/usr/bin/env bash
# Verify Mojo source is formatted. Mojo's `format` command has no --check
# flag in the current toolchain, so we format a copy and diff it against
# the real sources.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

tmp=$(mktemp -d)
trap "rm -rf '$tmp'" EXIT

cp -r src tests "$tmp/"
mojo format --quiet "$tmp/src" "$tmp/tests" >/dev/null 2>&1 || true

if ! diff -rq src "$tmp/src" >/dev/null 2>&1 || ! diff -rq tests "$tmp/tests" >/dev/null 2>&1; then
    echo "Formatting differences found. Run 'pixi run format' to fix:"
    diff -u src "$tmp/src" || true
    diff -u tests "$tmp/tests" || true
    exit 1
fi

echo "Formatting: clean."
