#!/usr/bin/env bash
# Install pixi (if missing) and provision the mojopi environment: Mojo 26.2 +
# MAX SDK + Python 3.12. Then run the Crawl-phase smoke + full test suite.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> 1/4 Checking for pixi"
if ! command -v pixi &>/dev/null; then
  echo "    pixi not found — installing via official installer"
  curl -fsSL https://pixi.sh/install.sh | bash
  # The installer writes the binary to ~/.pixi/bin. Add to PATH for this shell.
  export PATH="$HOME/.pixi/bin:$PATH"
  if ! command -v pixi &>/dev/null; then
    echo "    pixi install appeared to succeed but binary not on PATH."
    echo "    Add to your shell rc file:"
    echo '        export PATH="$HOME/.pixi/bin:$PATH"'
    echo "    then re-run this script."
    exit 1
  fi
  echo "    pixi installed → $(command -v pixi)"
  echo ""
  echo "    To make pixi persistent across shells, add to ~/.zshrc or ~/.bashrc:"
  echo '        export PATH="$HOME/.pixi/bin:$PATH"'
else
  echo "    pixi found: $(pixi --version)"
fi

echo ""
echo "==> 2/4 Provisioning environment (pulls Mojo + MAX SDK + Python 3.12)"
echo "    This may take several minutes on first run — large downloads."
if ! pixi install; then
  echo ""
  echo "    pixi install failed. Most common cause: package-name mismatch."
  echo "    The scaffolding agent guessed 'max = \"26.2.*\"' in pixi.toml."
  echo "    Modular's current packaging may use 'modular' instead."
  echo ""
  echo "    Try editing pixi.toml — in [dependencies], replace:"
  echo "        max = \"26.2.*\""
  echo "    with one of:"
  echo "        modular = \"*\"          # combined mojo+max package"
  echo "        max-pipelines = \"*\"    # pipelines-only package"
  echo ""
  echo "    Then re-run: ./scripts/bootstrap.sh"
  exit 1
fi

echo ""
echo "==> 3/4 Running smoke test (verifies Python interop reaches MAX)"
if pixi run smoke; then
  echo "    smoke: ok"
else
  echo "    smoke failed — check error above. Common causes:"
  echo "    - Mojo couldn't resolve 'from python import Python'"
  echo "    - The max package is installed but has a different module path"
  exit 1
fi

echo ""
echo "==> 4/4 Running full test suite (Mojo + Python)"
pixi run test

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next steps:"
echo "    pixi run test                  # run the full test suite"
echo "    pixi run smoke                 # confirm MAX version"
echo "    pixi run run -- -p 'hello'     # C3 one-shot demo (needs GGUF weights)"
echo ""
echo "Troubleshooting:"
echo "    If Mojo-side tests fail on syntax: the scaffolding agents targeted"
echo "    Mojo 26.2 but may have used APIs that churned. Fix as they surface."
echo "    PLAN.md §7 (risks) and §8 (open questions) track known drift."
