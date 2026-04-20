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
- GGUF weights for Llama-3.1-8B-Instruct. Reference build:
  [`modularai/Llama-3.1-8B-Instruct-GGUF`](https://huggingface.co/modularai/Llama-3.1-8B-Instruct-GGUF)
  (Q4_K_M recommended). Drop the `.gguf` into `models/` — it is gitignored.
- macOS on Apple Silicon (`osx-arm64`) or Linux x86_64 (`linux-64`).

## Quickstart

```bash
# Resolve the Mojo 26.2 + MAX + Python 3.12 environment.
pixi install

# Run the test suite — 22 tests (4 formatter + 5 read + 10 types + 3 interop).
pixi run test

# C1 smoke gate: Mojo→Python→MAX bridge prints a version string.
pixi run smoke

# C3 one-shot demo — first run downloads ~4.5GB of Llama-3.1-8B GGUF.
pixi run bash scripts/run.sh -p "What is 2+2? Answer briefly."

# Override the model / cap:
pixi run bash scripts/run.sh -p "hi" --model meta-llama/Llama-3.2-1B-Instruct --max-new-tokens 40
```

## Examples

```bash
# One-shot print mode
pixi run run -- -p "Explain list comprehensions in one sentence"

# Streaming JSON (for editor integrations)
pixi run run -- --mode json -p "Hello"

# Read prompt from file
pixi run run -- -p @my_prompt.txt

# Use a custom extension
pixi run run -- --extension my_ext.py -p "use my tool"
```

### Why `bash scripts/run.sh` and not `pixi run run -- …`?

Pixi 0.67 does not forward trailing arguments to string tasks. The shim
script sets `PYTHONPATH=src` and `mojo run -I src` so the Python interop
module (`max_brain.pipeline`) and Mojo modules resolve, then forwards
`"$@"` to the Mojo binary.

### Apple Silicon notes

MAX 26.2's sampling graph uses a `topk` kernel that requires an
`external memory` feature Apple's Metal GPU does not expose. The
generation path is pinned to `--devices cpu` in
[`src/max_brain/pipeline.py`](src/max_brain/pipeline.py). Expect ~1–3 tok/s
on an M-series CPU with Llama-3.1-8B Q4_K. GPU-accelerated generation is
a MAX upstream concern; Linux + CUDA should work without the CPU pin.

## Project layout

```
mojopi/
├── pixi.toml              # Mojo 26.2 + MAX + Python 3.12 manifest
├── README.md              # this file
├── AGENTS.md              # notes for future Claude agents
├── .gitignore
├── .github/               # CI workflows
├── scripts/               # one-off developer scripts
├── src/
│   ├── main.mojo          # entry point (CLI arg parse → agent loop)
│   ├── ai/                # message types, streaming primitives
│   ├── agent/             # AgentSession, AgentLoop, tool abstraction
│   ├── coding_agent/
│   │   └── tools/         # read, bash, edit, write, grep, find, ls
│   ├── max_brain/         # Python interop for MAX inference (GGUF, pipeline)
│   └── prompt/            # system prompt + ChatML formatter
└── tests/
    └── fixtures/          # golden fixtures for tool-parity tests
```

Domains above mirror the [pi-mono](https://github.com/badlogic/pi-mono) package
split (`ai` → `agent` → `coding-agent`) with `max_brain/` added for the MAX
pipeline glue. See [PLAN.md](PLAN.md) for the full 9-phase roadmap.

## Credits

Based on [pi-mono](https://github.com/badlogic/pi-mono) by Mario Zechner.
Port maintained against Mojo 26.2 and the MAX nightly channel.

## License

MIT — matches upstream pi-mono.
