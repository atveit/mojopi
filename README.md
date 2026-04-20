# mojopi

A Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono) — a local,
zero-network coding agent. The TypeScript `pi` binary becomes a single Mojo
process that drives the [Modular MAX](https://docs.modular.com/max/) engine for
on-device LLM inference, keeping pi-mono's ReAct loop, tool suite, and session
format intact. No remote API calls, no telemetry, no cloud dependency for
inference.

## Status (2026-04-20) — 🚀 v1.1.0

- 🎉 **v1.0 → v1.1 in one day** — full ReAct agent loop + 4 beyond-the-port features
- 🧠 **Semantic episodic memory** — local vector store, mlx-lm Metal embeddings, LLM-driven fact extraction → [docs/V1.1_FEATURES.md](docs/V1.1_FEATURES.md)
- ⚡ **Speculative decoding** — mlx-lm `draft_model=` wired; 1.5–2× speedup ready when a 1B draft is downloaded
- 💾 **KV cache persistence** — `~/.pi/sessions/<uuid>/kv_cache/` save 18 ms / load 1.3 ms for resumable sessions
- 🗜️ **TurboQuant KV quantization** — orthogonal-rotation + `mx.quantize`; **3.56× @ 4-bit**, **6.4× @ 2-bit** measured on M2 Max
- 🧪 **264 unit tests + 9 empirical** — full suite in ~70 s on M2 Max via `pixi run test`
- ⚙️ **MLX Metal fast-path** — 68 tok/s on Qwen3.5-4B-4bit, 192 tok/s on Qwen3-0.6B-4bit (4–12× vs MAX CPU)
- 🔌 **Extension API** — `register_tool`, `register_command`, `on(event)` auto-discovered from `~/.pi/agent/extensions/*.py`
- 🗂️ **Session v3** — 7-type JSONL with tree builder, compaction, branching → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 💬 **Interactive REPL** — slash commands (`/help`, `/file`, `/clear`, `/version`), rich markdown rendering → [docs/INTERACTIVE.md](docs/INTERACTIVE.md)
- 📤 **JSON/RPC output modes** — `--mode json` for streaming JSONL, `--mode rpc` for LSP-style editor integration
- 📦 **Packaging** — conda recipe + launcher for `pixi global install mojopi` → [docs/INSTALL.md](docs/INSTALL.md)
- 📜 **Release history** → [CHANGELOG.md](CHANGELOG.md) · [docs/V1_RELEASE.md](docs/V1_RELEASE.md) · [STATUS.md](STATUS.md) · [PLAN.md](PLAN.md)

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
