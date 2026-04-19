# AGENTS.md — notes for Claude agents working in this repo

This repository is a Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono)
(a TypeScript coding agent). The full plan lives at
[`../PLAN.md`](../PLAN.md). **Read §1 (target architecture) and §4 (phased
roadmap) before writing any code.** §5 explains the 8-agent domain split;
match the agent you're dispatched as against the file you're asked to touch.

## Conventions

- **Toolchain:** Mojo 26.2 and the MAX SDK, resolved via `pixi` from the
  `https://conda.modular.com/max-nightly/` channel. Do not pin against older
  Mojo versions — PRD-era API names (e.g. `std.io`) no longer exist.
- **`def`, not `fn`.** The modern Mojo compiler treats `def` as the default and
  `fn` is on the way out. `owned` is gone; transfer ownership with `^`.
- **Top-level stdlib imports.** Use `from pathlib import Path`, `from os import …`,
  `from io import …` — there is no `std.` prefix.
- **MAX is Python-first in 2026.** Do not try to call `max.engine` from Mojo
  directly; use `from python import Python` and drive MAX through
  `src/max_brain/*.py`. Reasoning in PLAN §0.
- **Session schema:** v3 only. See PLAN §3. Forward-compat is an explicit RFC,
  not a reflex.

## Scope discipline

- Stay inside your assigned module. Cross-domain edits need an explicit
  hand-off (PLAN §5).
- When landing work, update tests in the same module before calling the task
  done.
- Model weights (`*.gguf`, `models/`) are gitignored — never commit them.
