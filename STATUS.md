# Status

Running milestone tracker for [mojopi](https://github.com/atveit/mojopi) — a
Mojo/MAX port of [pi-mono](https://github.com/badlogic/pi-mono).
See **[PLAN.md](PLAN.md)** for the full 9-phase crawl/walk/run roadmap.

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
