# Architecture

High-level tour of the mojopi codebase. Read this first if you're new to the repo.

## Why Mojo + Python

mojopi is a Mojo program that calls Python for everything involving model
inference, tokenization, file I/O heuristics, and general Python-ecosystem
glue. The Mojo side owns:

- the CLI entry point (`main.mojo`)
- typed structs for history/tools/sessions (`agent/types.mojo`)
- the ReAct loop and tool dispatch (`agent/loop.mojo`, `agent/tool_executor.mojo`)

The Python side owns:

- MAX `TextGenerationPipeline` wrapping (`max_brain/pipeline.py`)
- MLX Metal inference (`max_brain/mlx_backend.py`)
- tool implementations (`coding_agent/tools/*.py`)
- session store, context loader, skills loader, hooks, extensions — all Python

Why: MAX is Python-first as of 2026, and Python has the mature ecosystem for
tokenizers, YAML frontmatter, glob walking, subprocess control, and hfcli-style
model downloads. Mojo's value add is type safety at the agent-loop level and
a binary that starts in < 50 ms without a Python import chain.

## Module map

```
src/
├── main.mojo                         # CLI entry point (parses args, routes to print/REPL)
├── cli/
│   ├── args.mojo                     # CliArgs struct + parse_args
│   └── print_helper.py               # @file expansion, stdin piping
├── agent/
│   ├── types.mojo                    # AgentTool, AgentContext, HistoryEntry, ParsedToolCall
│   ├── loop.mojo                     # ReAct loop: format → generate → extract → dispatch → iterate
│   ├── tool_executor.mojo            # Tool dispatch table with hook wiring
│   ├── hooks.py                      # before/after tool-call hook registry
│   ├── steering.py                   # Thread-safe steering queue (keyboard interrupt + file watcher)
│   ├── abort.py                      # threading.Event abort flag
│   ├── structured_output.py          # JSON-schema grammar path (GPU) + regex fallback
│   ├── output_mode.py                # JSON / RPC / print event formatters
│   └── parallel_dispatch.py          # Threading pool for read-only tool dispatch
├── coding_agent/
│   ├── tools/                        # 7 tools (read, write, edit, bash, grep, find, ls)
│   ├── session/                      # v3 JSONL store + tree builder
│   ├── context/                      # AGENTS.md walker + system prompt builder
│   ├── compaction/                   # 75% threshold summariser
│   ├── skills/                       # YAML-frontmatter skill loader
│   ├── extensions/                   # register_tool/command/event + discovery
│   └── tui/                          # textual TUI (streaming pane, tool-call collapsible)
├── max_brain/
│   ├── pipeline.py                   # MAX entrypoint (MAXModelConfig + DeviceSpec)
│   ├── mlx_backend.py                # MLX Metal inference (Apple Silicon)
│   ├── threaded_pipeline.py          # Dedicated inference thread (GIL isolation)
│   └── gil_profiler.py               # 100 Hz sampling GIL profiler
└── prompt/
    └── formatter.mojo                # ChatML formatting (pre-W2; loop.mojo now formats inline)
```

## The ReAct loop

`agent/loop.mojo::run_loop(user_input, context, model, max_new_tokens)`:

1. `clear_abort()`, `clear_steering()`
2. `fire_event("before_agent_start")`
3. Append user_input to history
4. For `iteration in 0..MAX_TOOL_ITERATIONS`:
   1. `if is_aborted(): return "[aborted]"`
   2. Poll steering queue → inject as user turn if any
   3. `format_history_as_chatml(system_prompt, history)`
   4. If prompt > 24 000 chars, trim middle turns (context guard)
   5. `fire_event("before_compact")`, `fire_event("message_start")`
   6. `max_brain.pipeline.generate_embedded(prompt, model, max_new_tokens)` →
      MLX → MAX embedded → subprocess fallback
   7. `fire_event("message_end")`
   8. `extract_tool_calls(response_text)`
   9. No tool calls → return response as final answer
   10. Otherwise append assistant message, dispatch each tool, append results

## The 8-backend fallback chain

```
arm64:  MLX Metal → MAX embedded (CPU-pinned) → MAX subprocess
x86_64: MAX embedded (auto device) → MAX subprocess
```

Every step catches its own exceptions and falls to the next. This means the
binary never crashes from a backend failure — it just gets slower.

## Session format (v3)

JSONL file under `~/.pi/sessions/<uuid>.jsonl`. Each line is one of 7 entry types:

- `session` — header (one per file)
- `message` — user / assistant / tool_result turn
- `thinking_level_change`
- `model_change`
- `compaction` — summary of trimmed-off history
- `branch_summary` — branch labels for resume
- `custom` / `custom_message`

A tree builder reconstructs branches from parent references and can resolve
a leaf_id to its full ancestor path. See `src/coding_agent/session/`.

## Extension API

Extensions are plain Python files. They import from `coding_agent.extensions.registry`
and `coding_agent.extensions.events`, then register at module load time.
Discovery: `~/.pi/agent/extensions/*.py`, `.pi/extensions/*.py`, `--extension <path>`.

Event taxonomy mirrors pi-mono's TypeScript `extensions/types.ts`:
`tool_call`, `message_start`, `message_end`, `before_agent_start`, `before_compact`,
`custom_event`.

## Tests

- **Mojo tests** (`tests/test_*.mojo`): type-level invariants, CLI parsing, Mojo-side
  hooks. Run with `pixi run test-mojo`.
- **Python tests** (`tests/test_*.py`): Python modules + cross-language integration
  via Python interop. Run with `pixi run test-python`.
- **Full suite** (`pixi run test`): 200+ tests, ~60 seconds.
- **Slow tests** (`@pytest.mark.slow`): require model weights; skipped in CI by default.

## Build flow

```
pixi install      # resolve Mojo 26.2 + MAX + Python 3.12 + textual + (pip: mlx, mlx-lm)
pixi run smoke    # C1 gate: Mojo → Python → MAX bridge works
pixi run test     # run all tests
pixi run run -- -p "hello"    # one-shot
pixi run run                  # interactive REPL
```

## The 14 empirical Mojo/MAX corrections

Catalogued in PLAN.md §0. Highlights:

- `from std.python import Python, PythonObject` (NOT `from python import Python`)
- `def f() raises:` — explicit on every function that can raise
- `.copy()` on every struct field access that flows into another struct
- `Int(py=obj)` not `Int(obj)` for Python ints
- `Python.evaluate("lambda x: x is None")` for None checks
- `comptime` for module-level constants (not `alias`)
- `tool_calls[i].copy()` when handing a struct to another call
- Don't iterate Python generators from Mojo — iterate in Python, return a list

## See also

- [PLAN.md](../PLAN.md) — 9-phase roadmap (crawl/walk/run)
- [BENCHMARKS.md](BENCHMARKS.md) — perf numbers
- [INTERACTIVE.md](INTERACTIVE.md) — using the REPL
- [EXTENSIONS.md](EXTENSIONS.md) — writing Python extensions
- [INSTALL.md](INSTALL.md) — installation
