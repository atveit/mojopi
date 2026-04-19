# Changelog

All notable changes to mojopi are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — v1.0.0-rc

### Added
- R3: `--mode json` streaming JSONL output; `--mode rpc` JSONL-RPC for editor integration
- R3: Parallel tool dispatch for read-only tools (read, grep, find, ls) via threading.Thread pool
- R3: Conda recipe + launcher script for `pixi global install mojopi`
- R2: Benchmark suite (`scripts/bench.py`) — TTFT, throughput, RSS, cold start
- R2: `--enable-structured-output` flag (GPU: JSON-Schema grammar; CPU: regex+retry)
- R2: GIL profiling infrastructure (`MaxInferencePool`, `profile_gil()`)
- R2: MAX pipeline API fix — `MAXModelConfig(model_path=..., device_specs=[DeviceSpec.cpu()])` replaces the broken `PipelineConfig(model=str, devices=str)` form
- R1: Python `textual` TUI — streaming pane, tool-call collapsible, keyboard interrupt → steering queue
- R1: Extension API — `register_tool`, `register_command`, `on(event)` with discovery from `~/.pi/agent/extensions/` and `.pi/extensions/`
- R1: 6-event bus (`tool_call`, `message_start`, `message_end`, `before_agent_start`, `before_compact`, `custom_event`)
- R1: Print mode hardening — `@file` expansion, stdin piping, `--system-prompt` / `--append-system-prompt`
- W3: Context compaction (75% threshold, summarise-and-trim via embedded pipeline)
- W3: Steering queue — keyboard/file-watcher injection into agent loop
- W3: Skills loader — YAML frontmatter, trigger filtering, global + project discovery
- W3: Abort flag with SIGTERM propagation to bash subprocess
- W3: `beforeToolCall` / `afterToolCall` hooks wired into `dispatch_tool()`
- W2: All 7 tools: read, grep, find, ls, bash, edit, write
- W2: ReAct agent loop with 8-turn cap and 3 retry on parse error
- W2: Full CLI arg parser (`CliArgs` struct)
- W1: Session store v3 (7 JSONL entry types), tree builder (`get_leaf_branches`, `resolve_path`)
- W1: AGENTS.md / CLAUDE.md context loader, system prompt builder
- W1: Embedded MAX `TextGenerationPipeline` cache (`get_or_create_pipeline`)
- C3: End-to-end `mojopi -p "…"` streaming tokens from MAX

### Performance (Apple M1 CPU, Llama-3.1-8B Q4_K_M)
- TTFT: ~1.95 s (cold start, includes model load)
- Throughput: ~15.4 tok/s (CPU; GPU target > 30 tok/s on Linux + CUDA)
- Apple GPU blocked by MAX 26.2 topk kernel — pinned to CPU on arm64

---

## [0.0.1] — 2026-04-19 (Crawl tier)

### Added
- C1: pixi environment — Mojo 26.2 + MAX + Python 3.12
- C2: Data types, `read` tool, MAX pipeline load
- C3: One-shot `mojopi -p "<prompt>"` — first token end-to-end
- 22/22 tests green at crawl close
