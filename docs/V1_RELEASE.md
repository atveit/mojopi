# v1.0.0 Release Notes

**Date:** 2026-04-20
**Tag:** `v1.0.0`
**Baseline:** pi-mono (TypeScript) → mojopi (Mojo + Python + MAX/MLX)

---

## What's in v1.0

### Core agent

- Full ReAct loop (`src/agent/loop.mojo`): format → generate → extract tool calls
  → dispatch → iterate. 10-turn cap. 3 retries on malformed JSON. Abort + steering
  checkpoints before every generation and every tool call.
- 7 tools: `read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`.
- Session v3 JSONL store with 7 entry types, tree builder, branch resolution.
- AGENTS.md / CLAUDE.md context loader with project (`.pi/SYSTEM.md`) and global
  (`~/.pi/agent/AGENTS.md`) overrides.
- Context compaction at 75% of window, summarise-and-trim.
- Skills loader (YAML frontmatter, trigger filtering).
- Abort flag with SIGTERM propagation into bash subprocess.
- Tool hooks (before / after) used as the substrate for the extension API.

### Inference backends

- **MLX Metal** (Apple Silicon fast-path): 68–193 tok/s observed on M2 Max —
  see [BENCHMARKS.md](BENCHMARKS.md).
- **MAX embedded** (cross-platform): Python `TextGenerationPipeline` via
  `MAXModelConfig(model_path=..., device_specs=[DeviceSpec.cpu()])`.
- **MAX subprocess** fallback (`max generate` CLI).

All three share a single cache and are transparent to the agent loop.

### CLI surface

- `-p / --print <prompt>` — one-shot print mode (tools enabled)
- interactive REPL with `/help`, `/exit`, `/clear`, `/version` slash commands
- `--mode json` — streaming JSONL of token/tool_call/tool_result/answer events
- `--mode rpc` — LSP-style Content-Length-framed JSONL for editor integration
- `@filepath` prompt expansion; stdin piping when `-p` has no argument
- `--system-prompt` / `--append-system-prompt`
- `--no-context-files`, `--tools t1,t2`, `--no-tools`
- `--session <uuid-prefix|path>` (parsed; resume wiring in a follow-up)
- `--enable-structured-output` for GPU JSON-schema grammar
- `--extension <path>` for loading a specific Python extension file

### Extension API

- `register_tool(name, fn, description, schema_json)`
- `register_command(name, fn)`
- `on(event, handler)` for 6 events: `tool_call`, `message_start`, `message_end`,
  `before_agent_start`, `before_compact`, `custom_event`
- Auto-discovery from `~/.pi/agent/extensions/*.py` and `.pi/extensions/*.py`
- Custom tools wrap Python callables into the `AgentTool` struct

### Performance infrastructure

- Benchmark suite (`scripts/bench.py`) measuring TTFT, throughput, RSS, cold start
- Nightly GitHub Actions workflow on macOS M1 runner
- GIL profiler + dedicated MAX inference thread (`MaxInferencePool`)
- Parallel tool dispatch for read-only tools via `threading.Thread` pool

### Distribution

- `conda-recipe/meta.yaml` + `scripts/mojopi.sh` launcher for
  `pixi global install mojopi`
- Pinned dependencies: `max==26.2.0`, `python==3.12.13`, `textual==8.2.4`,
  MLX stack via pip-bootstrap in the pixi env

---

## Testing

**200 tests** across 35 test files (12 Mojo + 23 Python). Runs in ~60 s.

```
pixi run test
```

Slow tests (`@pytest.mark.slow`) require model weights and are skipped in CI.
Three slow tests exist: `test_bench_with_model`, `test_get_or_create_pipeline_returns_object`,
`test_pipeline_cache_same_object`, `test_generate_embedded_returns_string`,
`test_mlx_generate_with_model`.

---

## Performance snapshot (M2 Max, 32 GB)

| Backend | Model | TTFT | Throughput |
|---------|-------|------|------------|
| MLX Metal | Qwen3-0.6B-4bit | 114 ms | **192.7 tok/s** |
| MLX Metal | Qwen3.5-4B-4bit | 298 ms | **68.6 tok/s** |
| MAX CPU | Llama-3.1-8B Q4_K_M | 1 950 ms | 15.4 tok/s |

NFR targets (TTFT < 150 ms, throughput > 30 tok/s) are **met** on MLX Metal.

---

## Known limitations

1. **Apple GPU sampling in MAX 26.2**: `topk` kernel hits an `external memory not
   supported on Apple GPU` constraint. Mitigated by MLX Metal fast-path; MAX is
   CPU-pinned on arm64.
2. **Session resume in interactive mode**: `--session` is parsed but the REPL
   doesn't yet rehydrate history from the session store. Follow-up task.
3. **Not every model emits `<tool_call>` syntax**: use Llama-3.1-Instruct-class
   models for tool-capable workflows. Small Qwen models are fine for throughput
   testing but will hallucinate tool results.
4. **TUI not yet auto-launched**: `coding_agent.tui` is built and tested but
   `main.mojo` uses a plain `input()` REPL. TUI launch from CLI is a v1.1 item.

---

## What's next (v1.1 and beyond)

- Session resume in interactive mode
- TUI auto-launch when stdout is a tty
- Linux + CUDA NFR validation (requires GPU CI runner)
- MLX speculative decoding
- `mlx-vlm` integration for vision-language models
- `pixi global install mojopi` published to a conda channel

---

## Upgrade path from v0.0.1 (Crawl)

No breaking changes for CLI users — `-p` still works. Internal Python and Mojo
APIs changed significantly:

- `max_brain.pipeline._make_pipeline_config` now uses `MAXModelConfig`
- `src/agent/loop.mojo::run_loop` signature changed to accept `AgentContext`
- Many new modules (output_mode, parallel_dispatch, mlx_backend, extensions,
  hooks, steering, abort, compaction, skills, tui, threaded_pipeline,
  gil_profiler, structured_output)

See [CHANGELOG.md](../CHANGELOG.md) for the full additive log.
