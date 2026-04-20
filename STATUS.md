# Status

Running milestone tracker for [mojopi](https://github.com/atveit/mojopi) — a
Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono).
See **[PLAN.md](PLAN.md)** for the full 9-phase crawl/walk/run roadmap.

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
