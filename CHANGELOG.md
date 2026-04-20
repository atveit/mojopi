# Changelog

All notable changes to mojopi are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.2.0] — 2026-04-20

### Added
- **Session resume** (`src/agent/session_manager.py`, `session_resolver.py`):
  `--session <prefix>` now resolves UUID prefixes, rehydrates history count,
  persists each turn to `~/.pi/sessions/<id>/transcript.jsonl`. 10 + 14 unit tests.
- **Thinking-token stripping** (`src/agent/thinking.py`): strips `<think>`,
  `<thinking>`, `<|thinking|>`, ```thinking``` blocks before tool-call
  extraction. Reasoning models unblocked. 14 unit tests.
- **Parse-retry scaffold** (`src/agent/parse_retry.py`): re-prompt with format
  reminder up to 3× when model emits JSON-shaped output without `<tool_call>`
  tags. 7 unit tests.
- **Turn-cap summarization** (`src/agent/turn_summary.py`): loop.mojo no
  longer returns `"[agent: max tool iterations reached]"`; produces readable
  summary of user request + tool log + partial findings. 9 unit tests.
- **Auto-compaction bridge** (`src/agent/compaction_bridge.py`): exposes the
  W3 compaction module as a loop-callable policy with token-budget trigger.
  8 unit tests.
- **Auto-memory bridge** (`src/coding_agent/memory/auto_inject.py`):
  `augment_system_prompt()` and `extract_after_session()` for opt-in memory
  wiring. 11 unit tests.
- **Tool-calling verification** (`scripts/verify_tool_calling.py`): detects
  cached tool-capable MLX models and runs empirical smoke test. 5 slow tests.
- `docs/V1.2_GAP_CLOSURE.md` — functional-parity planning doc.

### Wired
- `main.mojo` REPL: `/session` slash command; auto-save per turn; session
  prefix resolution on launch; rehydrate count display.
- `loop.mojo`: `strip_thinking_text()` before every `extract_tool_calls`;
  `summarize_turn_cap()` replaces the turn-cap placeholder.

### Not wired (opt-in via Python for now)
- Auto-memory injection into agent loop (needs real-model eval first)
- Auto-compaction trigger in agent loop (needs prompt-budget tuning first)

### Test counts
**355 Python + 12 Mojo** tests collected — up from 264 at v1.1.0.

---

## [1.1.0] — 2026-04-20

### Added
- **Semantic episodic memory** (`src/coding_agent/memory/`) — JSONL vector store,
  mlx-lm Metal embeddings, bag-of-words fallback, LLM-driven fact extraction,
  top-k cosine retrieval. 17 unit + 2 empirical tests.
- **Speculative decoding** (`src/max_brain/speculative.py`) — mlx-lm
  `draft_model=` integration with graceful fallback. 12 unit + 2 empirical tests.
- **KV cache persistence** (`src/max_brain/kv_cache.py`) — per-layer safetensors
  under `~/.pi/sessions/<uuid>/kv_cache/`. 13 unit + 2 empirical tests.
- **TurboQuant** (`src/max_brain/turboquant.py`) — MLX `mx.quantize` with
  deterministic orthogonal rotation; 2/3/4/8-bit modes. Empirical 3.56×
  reduction at 4-bit, 6.4× at 2-bit. 12 unit + 3 empirical tests.
- `tests/test_v1_1_empirical.py` — 9 `@pytest.mark.slow` empirical tests
  (7 pass, 2 skip when real MLX cache shapes don't align with group_size).
- `docs/V1.1_FEATURES.md` — full design, API, and measured numbers.
- `docs/V1.1_AMBITIOUS.md` — planning document for the four-agent parallel dispatch.
- Test count: **264 unit + 9 empirical** (up from 210 at v1.0.1).

---

## [1.0.1] — 2026-04-20

### Added
- `cli/repl_helper.py` — Rich markdown rendering, env var defaults
  (`MOJOPI_MODEL`, `MOJOPI_MAX_NEW_TOKENS`), `/file <path>` slash command.

---

## [1.0.0] — 2026-04-20

### Added
- Full ReAct loop wired into `main.mojo` (print + interactive REPL)
- MLX Metal backend as arm64 default (`src/max_brain/mlx_backend.py`)
- Pinned deps: `max==26.2.0`, `python==3.12.13`, `textual==8.2.4`
- Docs: ARCHITECTURE, INTERACTIVE, BENCHMARKS, V1_RELEASE

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
