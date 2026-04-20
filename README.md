# mojopi

A Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono) — a local,
zero-network coding agent. The TypeScript `pi` binary becomes a single Mojo
process that drives the [Modular MAX](https://docs.modular.com/max/) engine for
on-device LLM inference, keeping pi-mono's ReAct loop, tool suite, and session
format intact. No remote API calls, no telemetry, no cloud dependency for
inference.

## Status (2026-04-20) — 🖥️ v1.3.0 — Mac-native UX + loop improvements

- 🖥️ **Mac menu bar app** — 🤖 in the tray → "Ask mojopi…" → Cocoa input → answer in an alert (`src/coding_agent/ui/menubar/`)
- 📱 **SwiftUI native chat app** — Xcode 26.1.1 Swift Package at `apps/mojopi-mac/`; `swift build -c release` produces a 204 KB arm64 binary; ⌘N new session, ⌘K clear
- 🧭 **Expanded slash commands** — `/model`, `/history`, `/save`, `/fork`, `/tokens`, `/memory list|add|forget` — 18 tests → [docs/INTERACTIVE.md](docs/INTERACTIVE.md)
- 🔎 **Session search** — `mojopi search "auth token"` greps all session transcripts with snippet + role + timestamp
- ⚙️ **.env auto-loaded** — `./​.env` + `~/.pi/.env` exported to `os.environ` before CliArgs
- 📥 **`scripts/fetch_model.sh`** — preflight disk + mlx-lm download with exit-code semantics
- ⚡ **Parallel tool dispatch module** — 3× speedup on read-only batches (opt-in from Python; loop wiring is v1.4)
- 🧩 **Gemma `<|channel>thought<channel|>` stripped**; friendly error messages translate pydantic/HF exceptions
- ✅ **Real tool-calling proven** — Gemma 4 e4b emits proper `<tool_call>` tags → [docs/MODEL_VERIFICATION.md](docs/MODEL_VERIFICATION.md)
- 🏗️ **Crawl → Walk → Run test pyramid** — 6 crawl + 12 walk + 6 run integration tests against real Gemma 4
- 🎯 **v1.0 → v1.1 → v1.2 → v1.3 in one day** — full ReAct loop + 4 beyond-the-port features + 7 functional gaps closed + Mac UX → [docs/V1.3_PLAN.md](docs/V1.3_PLAN.md)
- 📂 **Session resume actually works** — `--session <uuid-prefix>` resolves, rehydrates, persists each turn to `~/.pi/sessions/<id>/transcript.jsonl`
- 🧩 **Reasoning models unblocked** — `<think>`, `<thinking>`, `<|thinking|>` blocks stripped before tool-call extraction in `loop.mojo`
- 📊 **Turn-cap summarization** — no more `"[max tool iterations reached]"` placeholder; agent produces a readable summary of request + tool log + partial findings
- 🧠 **Semantic episodic memory** — local vector store, mlx-lm Metal embeddings, LLM-driven fact extraction → [docs/V1.1_FEATURES.md](docs/V1.1_FEATURES.md)
- ⚡ **Speculative decoding** — mlx-lm `draft_model=` wired with graceful fallback; 1.5–2× speedup ready when a 1B draft is downloaded
- 💾 **KV cache persistence** — `~/.pi/sessions/<uuid>/kv_cache/` save 18 ms / load 1.3 ms
- 🗜️ **TurboQuant KV quantization** — orthogonal-rotation + `mx.quantize`; **3.56× @ 4-bit**, **6.4× @ 2-bit** measured on M2 Max
- ⚙️ **MLX Metal fast-path** — 68 tok/s on Qwen3.5-4B-4bit, 192 tok/s on Qwen3-0.6B-4bit, TTFT 281 ms on Gemma 4 e4b (4–12× vs MAX CPU) → [docs/BENCHMARKS.md](docs/BENCHMARKS.md)
- 🧪 **505 tests total (498 pass + 7 skipped)** — up from 431 at v1.2.0; fast suite ~195 s on M2 Max; slow tier runs real MLX inference
- 🔌 **Extension API** — `register_tool`, `register_command`, `on(event)` auto-discovered from `~/.pi/agent/extensions/*.py` → [docs/EXTENSIONS.md](docs/EXTENSIONS.md)
- 🗂️ **Session v3** — 7-type JSONL with tree builder, compaction, branching → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 💬 **Interactive REPL** — `/session`, `/file`, `/help`, `/clear`, `/version` slash commands, rich markdown rendering → [docs/INTERACTIVE.md](docs/INTERACTIVE.md)
- 📤 **JSON/RPC output modes** — `--mode json` for streaming JSONL, `--mode rpc` for LSP-style editor integration
- 📦 **Packaging** — conda recipe + launcher for `pixi global install mojopi` → [docs/INSTALL.md](docs/INSTALL.md)
- 📜 **Release history** → [CHANGELOG.md](CHANGELOG.md) · [docs/V1_RELEASE.md](docs/V1_RELEASE.md) · [STATUS.md](STATUS.md) · [PLAN.md](PLAN.md)

### Preferred model — Gemma 4 e4b

```bash
# Download once (~2.3 GB, ~3 min on typical broadband)
pixi run python -c "from mlx_lm import load; load('mlx-community/gemma-4-e4b-it-4bit')"

# Run mojopi with it
pixi run run -- -p "What does README.md contain? Use the read tool." \
    --model mlx-community/gemma-4-e4b-it-4bit
```

See [docs/MODEL_VERIFICATION.md](docs/MODEL_VERIFICATION.md) for why Gemma 4 beats
Qwen3/Llama 3.2 for tool-use workflows (short version: Gemma 4 emits the tag format
natively without prompt-engineering hacks).

## Prerequisites

- [pixi](https://pixi.sh) installed (`curl -fsSL https://pixi.sh/install.sh | bash`).
- macOS 14+ on Apple Silicon (`osx-arm64`) or Linux x86_64 (`linux-64`).
- A tool-capable MLX model. **Recommended: Gemma 4 e4b** (~2.3 GB, verified).
  Fetch once with the helper:
  ```bash
  scripts/fetch_model.sh gemma-4-e4b-it-4bit
  ```
- For the SwiftUI app: Xcode 14+ (macOS 14+ SDK).

## Quickstart

```bash
# 1. Resolve the Mojo 26.2 + MAX + Python 3.12 + MLX environment.
pixi install

# 2. Run the fast test suite (498 tests, ~195 s on M2 Max).
pixi run test

# 3. C1 smoke gate — Mojo→Python→MAX bridge prints a version string.
pixi run smoke

# 4. One-shot prompt (downloads the model on first run).
scripts/fetch_model.sh gemma-4-e4b-it-4bit     # ~2.3 GB, once
pixi run bash scripts/run.sh -p "What is 2+2? Answer briefly." \
    --model mlx-community/gemma-4-e4b-it-4bit

# 5. Interactive REPL — /help lists all slash commands.
pixi run bash scripts/run.sh --model mlx-community/gemma-4-e4b-it-4bit
```

Set defaults once in `.env` (or `~/.pi/.env`) so you don't have to pass
`--model` every time:

```
MOJOPI_MODEL=mlx-community/gemma-4-e4b-it-4bit
MOJOPI_MAX_NEW_TOKENS=256
MOJOPI_AUTO_MEMORY=1
```

## Examples

```bash
# Interactive chat
pixi run bash scripts/run.sh

# One-shot print mode
pixi run bash scripts/run.sh -p "Explain list comprehensions in one sentence"

# Streaming JSON output for editor integrations
pixi run bash scripts/run.sh -p "Hello" --mode json

# Read prompt from file (or pipe via stdin)
pixi run bash scripts/run.sh -p @my_prompt.txt

# Full-text search across past sessions
pixi run bash scripts/run.sh search "auth token"

# Mac menu bar app (tray icon — experimental)
pixi run python -m coding_agent.ui.menubar.menubar

# SwiftUI native Mac app (requires Xcode)
(cd apps/mojopi-mac && swift build -c release)
./apps/mojopi-mac/.build/release/mojopi-mac
```

### Why `bash scripts/run.sh` and not `pixi run run -- …`?

Pixi does not forward trailing arguments to string tasks. The shim script
sets `PYTHONPATH=src` and `mojo run -I src` so the Python interop modules
and Mojo packages resolve, then forwards `"$@"` to the Mojo binary.

### Apple Silicon performance

MAX 26.2's `topk` sampler hits an `external memory not supported on Apple
GPU` constraint, so mojopi routes Apple Silicon through **MLX Metal** via
[`src/max_brain/mlx_backend.py`](src/max_brain/mlx_backend.py) instead —
cleanly 4–12× faster than MAX CPU. Measured on M2 Max:

| Backend | Model | TTFT | Throughput |
|---------|-------|------|------------|
| MLX Metal | Gemma 4 e4b (4-bit) | 281 ms | ~40 tok/s |
| MLX Metal | Qwen3-0.6B (4-bit) | 114 ms | 192 tok/s |
| MLX Metal | Qwen3.5-4B (4-bit) | 298 ms | 68 tok/s |
| MAX CPU   | Llama-3.1-8B Q4_K   | 1 950 ms | 15 tok/s |

Linux + CUDA uses the MAX embedded path (unaffected by the Apple topk bug).
See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for the full table and
[docs/MODEL_VERIFICATION.md](docs/MODEL_VERIFICATION.md) for which models
emit `<tool_call>` tags out of the box.

## Project layout

```
mojopi/
├── pixi.toml                     # Mojo 26.2 + MAX + Python 3.12 (+ pip-bootstrap MLX)
├── README.md                     # this file
├── AGENTS.md                     # notes for future Claude agents
├── CHANGELOG.md · PLAN.md · STATUS.md
├── apps/
│   └── mojopi-mac/               # SwiftUI native Mac app (Swift Package)
├── docs/                         # ARCHITECTURE, INTERACTIVE, BENCHMARKS,
│                                 #   INSTALL, EXTENSIONS, V1.1_FEATURES,
│                                 #   V1.2_GAP_CLOSURE, V1.3_PLAN, MODEL_VERIFICATION …
├── scripts/                      # run, smoke, bench, bench_speculative,
│                                 #   fetch_model, mojopi (conda launcher), …
├── src/
│   ├── main.mojo                 # CLI → env loader → slash commands → REPL / print
│   ├── ai/                       # Message types
│   ├── agent/
│   │   ├── loop.mojo             # ReAct loop (abort/steering/think/summary)
│   │   ├── types.mojo, tool_executor.mojo, hooks, steering, abort,
│   │   ├── structured_output, output_mode, parallel_dispatch, parallel_loop,
│   │   ├── session_manager, session_resolver, thinking, parse_retry,
│   │   └── compaction_bridge, turn_summary
│   ├── cli/
│   │   ├── args.mojo, print_helper, repl_helper
│   │   ├── slash_commands, search, env_loader
│   ├── coding_agent/
│   │   ├── tools/                # read, write, edit, bash, grep, find, ls
│   │   ├── session/              # v3 JSONL store + tree builder
│   │   ├── context/              # AGENTS.md walker + system prompt builder
│   │   ├── compaction/           # 75% threshold summariser
│   │   ├── skills/               # YAML-frontmatter skill loader
│   │   ├── extensions/           # register_tool/command/event + discovery
│   │   ├── memory/               # vector store + mlx embeddings + extraction
│   │   ├── tui/                  # textual TUI (built, not auto-launched)
│   │   └── ui/menubar/           # Mac menu bar app (rumps)
│   ├── max_brain/
│   │   ├── pipeline.py           # MAX entrypoint (MAXModelConfig)
│   │   ├── mlx_backend.py        # MLX Metal fast-path (Apple Silicon default)
│   │   ├── threaded_pipeline, gil_profiler,
│   │   ├── speculative,          # mlx-lm draft_model= wiring
│   │   ├── kv_cache,             # save/load prompt cache to disk
│   │   ├── turboquant,           # 4-bit / 2-bit KV cache quantization
│   │   └── error_messages        # friendly pydantic/HF translations
│   └── prompt/                   # ChatML formatter (pre-W2; loop now inlines)
├── tests/                        # 505 tests: unit + integration + end-to-end
│   ├── test_integration_coverage.py   (38 tests — one per functional area)
│   ├── test_walk_integration.py       (12 tests — multi-turn tool chains, mocked LLM)
│   ├── test_run_integration.py        (6 tests — real Gemma 4 end-to-end)
│   ├── test_end_to_end.py             (6 tests — binary + subprocess smoke)
│   └── fixtures/                 # golden fixtures for tool-parity tests
└── conda-recipe/                 # `pixi global install mojopi` recipe
```

Domains mirror [pi-mono](https://github.com/badlogic/pi-mono)'s package split
(`ai → agent → coding_agent`) with `max_brain/` and `cli/` added, plus the
Mac UI bits in `apps/` and `src/coding_agent/ui/`. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component deep-dive and
[PLAN.md](PLAN.md) for the original 9-phase roadmap (all phases closed at v1.0).

## Credits

Based on [pi-mono](https://github.com/badlogic/pi-mono) by Mario Zechner.
Port maintained against Mojo 26.2 and the MAX nightly channel.

## License

MIT — matches upstream pi-mono.
