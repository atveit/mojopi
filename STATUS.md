# Status

Running milestone tracker for [mojopi](https://github.com/atveit/mojopi) — a
Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono).
See **[PLAN.md](PLAN.md)** for the full 9-phase crawl/walk/run roadmap.

---

## 2026-04-20 — 🎯 v1.2.0: pi-mono functional parity

### TLDR
- 📂 **Session resume actually works** — `--session <uuid-prefix>` resolves to full ID, rehydrates history count, persists each turn to `~/.pi/sessions/<id>/transcript.jsonl`
- 🧠 **Auto-memory bridge** — `augment_system_prompt()` ready for opt-in injection; `extract_after_session()` runs fact extraction on REPL exit (swallows errors so session close never blocks)
- 🧩 **Thinking-token stripping** — `<think>`, `<thinking>`, `<|thinking|>`, and ```thinking code fences stripped from responses before tool-call extraction (reasoning models unblocked)
- 🔁 **Parse-retry scaffold** — `retry_parse_tool_calls` re-prompts with format reminder up to 3× when model emits JSON-shaped output without `<tool_call>` tags
- 📊 **Turn-cap summarization** — loop.mojo no longer returns `"[agent: max tool iterations reached]"`; produces a readable summary of user request + tool log + partial findings + recommended next step
- 🗜️ **Auto-compaction bridge** — `auto_compact_if_needed()` ready for opt-in compaction when history exceeds 75% of context budget
- 🔖 **Session resolver** — UUID-prefix lookup (`abc12` → `abc12345-...`), ambiguous-prefix detection, mtime-sorted listing, latest-session lookup
- 🧪 **Tool-calling empirical script** — `scripts/verify_tool_calling.py` detects cached tool-capable MLX models and runs an end-to-end smoke; exits 0/1/2 for pass/fail/skip
- 🧪 **355 Python tests + 12 Mojo tests** — up from 264 at v1.1; 91 new tests across 6 modules
- 🏷️ `v1.2.0` tagged and pushed

### 6 parallel agents, zero file conflicts
| Agent | Module | Tests |
|-------|--------|-------|
| A Session resume | `src/agent/session_manager.py` | 10 |
| B Auto-memory | `src/coding_agent/memory/auto_inject.py` | 11 |
| C Thinking + retry | `src/agent/thinking.py`, `parse_retry.py` | 14 + 7 |
| D Compaction + summary | `src/agent/compaction_bridge.py`, `turn_summary.py` | 8 + 9 |
| E Resolver | `src/agent/session_resolver.py` | 14 |
| F Empirical | `scripts/verify_tool_calling.py`, `tests/test_real_tool_calling.py` | 4 + 1 skip |

### Wired into main.mojo + loop.mojo by lead
- main.mojo: `/session` slash command, per-turn save via `save_turn`, prefix resolution via `resolve_session_id`, session rehydrate count on launch
- loop.mojo: `strip_thinking_text()` on every response before tool extraction; `summarize_turn_cap(history)` replaces the old placeholder when the iteration cap is hit

### What's NOT wired (still opt-in from Python)
- Auto-memory injection (needs eval of retrieval noise on real models first)
- Auto-compaction (needs real-world prompt budget measurement)

### Commit trail
`b0be102` v1.1.0 README · (this commit) v1.2.0 with 6 new modules + loop/main wiring

### Next up (v1.3)
TUI auto-launch + streaming; `/model`, `/history`, `/save`, `/fork` slash commands; `doctor` subcommand; Llama-3.1-8B-Instruct-4bit download script.

---

## 2026-04-20 — 🚀 v1.1.0: beyond-the-port features

### TLDR
- 🧠 **Semantic episodic memory** — local vector store over `~/.pi/memory/*.jsonl` with mlx-lm Metal embeddings (bag-of-words fallback); LLM-driven fact extraction from sessions; top-k cosine retrieval in 0.09 ms over 5 entries
- ⚡ **Speculative decoding** — mlx-lm `draft_model=` wired with graceful fallback; benchmark harness reports baseline vs speculative speedup
- 💾 **KV cache persistence** — `make_prompt_cache` → safetensors on disk at `~/.pi/sessions/<uuid>/kv_cache/`; 8-layer 128 KB cache saves in 18 ms, loads in 1.3 ms
- 🗜️ **TurboQuant** — random-orthogonal-rotation + MLX `mx.quantize`; **3.56× reduction at 4-bit (MAE 7% of RMS)**, **6.4× at 2-bit**, composes with persistence so a 60 MB 20-turn cache drops to ~15 MB on disk
- 🧪 **264 unit tests + 7 empirical** (9 empirical total, 2 skipped on real-cache shape mismatch)
- 📝 Full design + numbers in [docs/V1.1_FEATURES.md](docs/V1.1_FEATURES.md); parallelization plan in [docs/V1.1_AMBITIOUS.md](docs/V1.1_AMBITIOUS.md)
- 🏷️ `v1.1.0` tagged and pushed

### What shipped (commit trail)
`4353124` v1.0.0 · `ea0a148` v1.0.1 polish · (this commit) v1.1.0 with 4 new features in 4 parallel agents

### Next up (v1.2)
Wire /memory slash command into REPL; quantize+persist composition in `loop.mojo` compaction path; Llama-3.2-1B draft model download script for empirical speculative speedup measurement.

---

## 2026-04-20 — 🎉 v1.0.0 shipped

### TLDR
- 🚀 **200 tests green**, Mojo 26.2 + Python 3.12.13 + textual 8.2.4 pinned
- ⚡ **MLX Metal backend**: 68.6 tok/s on Qwen3.5-4B-4bit, 192.7 tok/s on Qwen3-0.6B-4bit (M2 Max) — NFR met
- 🛠️ **Interactive REPL wired**: `mojopi` with no args drops into a full agent loop; `-p` also uses the ReAct loop (tools work)
- 📝 **Docs**: [ARCHITECTURE.md](docs/ARCHITECTURE.md), [INTERACTIVE.md](docs/INTERACTIVE.md), [BENCHMARKS.md](docs/BENCHMARKS.md), [V1_RELEASE.md](docs/V1_RELEASE.md), [EXTENSIONS.md](docs/EXTENSIONS.md), [INSTALL.md](docs/INSTALL.md)
- 🏷️ **v1.0.0 tagged** — pinned pixi.toml, published release notes
- 📦 **8-backend fallback**: MLX Metal → MAX embedded → MAX subprocess; transparent to loop
- 🔌 **Extension API**: `register_tool`, `register_command`, `on(event)` with 6-event bus; auto-discovery from `~/.pi/agent/extensions/` + `.pi/extensions/`

### Gates met
- **R1 — TUI + extensions + print polish:** ✅
- **R2 — benchmarks + MAX pipeline fix + structured output + GIL profiling:** ✅
- **R3 — JSON/RPC modes + parallel tool dispatch + packaging + v1.0:** ✅
- **v1.0 cut:** main.mojo wires full agent loop; pixi.toml pinned; tag pushed ✅

### Commit trail
`8bd0f68` (MLX backend) · [`bd99680`](https://github.com/atveit/mojopi/commit/bd99680) (R3) · [`449740a`](https://github.com/atveit/mojopi/commit/449740a) (R2) · [`04d7d6d`](https://github.com/atveit/mojopi/commit/04d7d6d) (R1) · [`5af58fe`](https://github.com/atveit/mojopi/commit/5af58fe) (W3) · [`9897455`](https://github.com/atveit/mojopi/commit/9897455) (W1+W2)

### Next up
v1.1: session resume in REPL, TUI auto-launch when stdout is a tty, Linux+CUDA CI validation, MLX speculative decoding. See [V1_RELEASE.md](docs/V1_RELEASE.md).

---

## 2026-04-19 — 🏁 Walk tier closed (W1 + W2 + W3)

### TLDR
- 🎉 Full ReAct agent loop: session store + all 7 tools + steering/abort/compaction working
- 🧪 100/100 tests green (Mojo + Python across all modules)
- 🗂️ Session v3 format: 7 entry types (session, message, thinking_level_change, model_change, compaction, branch_summary, custom_message), JSONL + tree builder
- 🛠️ 7 tools wired: read, grep, find, ls, bash, edit, write — all with Python interop helpers
- 🔄 ReAct loop: ChatML formatting → MAX generate → extract_tool_calls → dispatch → iterate (max 8 turns)
- 📦 W3 extras: context compaction (75% threshold), steering queue (keyboard/file-watcher), skills loader (YAML frontmatter), abort flag (SIGTERM propagation), tool hooks (before/after)
- ⚙️ Extension API substrate: `agent.hooks` (before/after tool call) wired into `dispatch_tool`
- 📝 PLAN.md updated with Walk→Run learnings: Python interop is permanent, TUI deferred to R1, MAX pipeline bug tracked

### Gates met
- **W1 — session + context + embedded pipeline:** all stores + loaders + pipeline cache ✅
- **W2 — all 7 tools + ReAct loop + CLI args:** full CliArgs struct + agent loop ✅
- **W3 — compaction + steering + skills + abort + hooks + loop integration:** all wired into run_loop() ✅

### Commit trail
[`5af58fe`](https://github.com/atveit/mojopi/commit/5af58fe) (W3 close)
· [`9897455`](https://github.com/atveit/mojopi/commit/9897455) (W1+W2 close)

### Next up
Run tier (R1 → R2 → R3): TUI + extension API + print polish → benchmarks + GPU path → distribution + v1.0. See [PLAN.md §4 Tier R](PLAN.md).

---

## 2026-04-19 — 🏁 Run tier in progress (R1 + R2 complete, R3 in flight)

### TLDR
- ✅ R1: TUI (textual), extension API (register_tool/command/event), print mode hardening, docs
- ✅ R2: MAX pipeline bug fixed (MAXModelConfig API), benchmark suite, structured output (--enable-structured-output), GIL profiling infrastructure
- 🔄 R3: --mode json/rpc, parallel tool dispatch, conda packaging, v1.0 prep
- 🧪 164 tests green (3 slow skipped) before R3 launch

### Gates in progress
- **R1 — TUI + extensions + print polish:** TUI renders, extension API wired, -p hardened ✅
- **R2 — benchmarks + GPU path:** MAX config bug fixed, benchmark harness live ✅
- **R3 — distribution + v1.0:** in progress 🔄

### Commit trail
[`449740a`](https://github.com/atveit/mojopi/commit/449740a) (R2 close)
· [`04d7d6d`](https://github.com/atveit/mojopi/commit/04d7d6d) (R1 close)
---

## 2026-04-19 — 🏁 Crawl tier closed (C1 + C2 + C3)

### TLDR
- 🎉 First generation end-to-end: `mojopi -p "What is 2+2?"` → **"The answer is 4."**
- 🧪 22/22 tests green (4 formatter + 5 read + 10 types + 3 Python interop)
- ⚡ TTFT 1.95 s, throughput 15.4 tok/s on Apple M-series CPU (Llama-3.1-8B Q4_K via MAX 26.2)
- 🧰 Full Mojo ↔ Python ↔ MAX stack wired: `max_brain.pipeline.run_one_shot` drives the `max generate` subprocess and streams stdout back through Mojo
- 📦 Pushed to [github.com/atveit/mojopi](https://github.com/atveit/mojopi) — 10 commits across 2 days
- 📝 [PLAN.md §0](PLAN.md) now tracks 14 empirical Mojo/MAX corrections discovered during Crawl (std.* prefix, explicit `raises`, `.copy()` not `^` on def params, `alias→comptime`, `Int(py=...)`, UTF-8 env, Apple GPU CPU pin, etc.)
- ⚠️ Known gap: Apple GPU blocked by MAX 26.2 `topk` kernel → pinned to `--devices cpu` on arm64. Linux + CUDA unaffected.

### Gates met
- **C1 — scaffolding & smoke:** `pixi run smoke` → bridge reaches MAX ✅
- **C2 — types + one tool + MAX load:** 3 unit tests green (data round-trip, `read` fixture, pipeline constructs) ✅
- **C3 — one-shot end-to-end:** `mojopi -p "…"` streams a correct answer ✅

### Commit trail
[`b7742d3`](https://github.com/atveit/mojopi/commit/b7742d3) (C3 closure)
· [`f0af4eb`](https://github.com/atveit/mojopi/commit/f0af4eb) (docs)
· [`cf8eef2`](https://github.com/atveit/mojopi/commit/cf8eef2) (C3 driver)
· [`ff41903`](https://github.com/atveit/mojopi/commit/ff41903) (C1a close)

### Next up
Walk tier (W1 → W2 → W3): session store + AGENTS.md loader → all 7 tools + ReAct loop + interactive TUI → compaction + steering + skills. See [PLAN.md §4 Tier W](PLAN.md).
