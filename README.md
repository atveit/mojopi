# mojopi

A Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono) — a local,
zero-network coding agent. The TypeScript `pi` binary becomes a single Mojo
process that drives the [Modular MAX](https://docs.modular.com/max/) engine for
on-device LLM inference, keeping pi-mono's ReAct loop, tool suite, and session
format intact. No remote API calls, no telemetry, no cloud dependency for
inference.

## Status

🚧 **Crawl phase** — scaffolding and smoke tests only. The agent loop, tools,
and TUI land in the Walk phase; see [../PLAN.md](../PLAN.md) for the full
9-phase roadmap (C1 → R3) and weekly milestones.

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

# Run the test suite (Mojo tests, then pytest).
pixi run test

# C1 smoke gate: import max and print its version.
pixi run smoke

# One-shot prompt (works from C3 onward).
pixi run run -- -p "hello"
```

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
pipeline glue. See [../PLAN.md](../PLAN.md) for the full 9-phase roadmap.

## Credits

Based on [pi-mono](https://github.com/badlogic/pi-mono) by Mario Zechner.
Port maintained against Mojo 26.2 and the MAX nightly channel.

## License

MIT — matches upstream pi-mono.
