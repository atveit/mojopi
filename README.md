# mojopi

A Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono) — a local,
zero-network coding agent. The TypeScript `pi` binary becomes a single Mojo
process that drives the [Modular MAX](https://docs.modular.com/max/) engine for
on-device LLM inference, keeping pi-mono's ReAct loop, tool suite, and session
format intact. No remote API calls, no telemetry, no cloud dependency for
inference.

## Status

🏁 **Crawl tier closed (2026-04-19)** — first generation end-to-end,
22/22 tests green. See [STATUS.md](STATUS.md) for the TLDR and
[PLAN.md](PLAN.md) for the full 9-phase roadmap. Agent loop, tools,
and TUI land in the Walk tier next.

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
