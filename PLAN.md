# PLAN: Porting `pi-mono` to Mojo / Modular MAX

**Status:** Draft v1 · **Date:** 2026-04-18 · **Source PRD:** `MojoPi.pdf`
**Scope:** Port `pi-mono/packages/coding-agent` (+ its dependency chain `agent` → `ai` → `tui`) to a Mojo binary that uses the Modular MAX engine for local inference. Mom, Pods, and Web-UI are **out of scope** for this port.

---

## 0. Corrections to the source PRD

The PRD is directionally right but cites several Mojo/MAX APIs that have moved or don't exist as written. The plan uses the current (2026-04) state:

| PRD claim | Actual state (2026-04) |
|---|---|
| `std.subprocess`, `std.os.pathlib`, `std.io` | ~~No `std.` namespace~~ **Correction (empirical, C1):** `std.` prefix IS required in pixi-installed Mojo. Use `from std.python import Python`, `from std.collections import List`, `from std.pathlib import Path`, `from std.testing import assert_equal`, `from std.sys import argv`. Implicit (unprefixed) imports emit a deprecation warning and will break in a future release. |
| `magic` package manager | Merged into upstream `pixi`. Scaffold with `pixi init -c https://conda.modular.com/max-nightly/`. |
| Mojo `max.engine.InferenceSession` | Mojo `max.engine` is **deprecated**. MAX is Python-first. Call via `from python import Python`. |
| `max.kv_cache.PagedKVCacheManager` | Exists but in the **Python** `max.kv_cache` module, not Mojo. |
| `fn … raises` as canonical | `fn` deprecated in favor of `def`. **Correction (empirical, C1):** `def` does NOT implicitly raise in the pixi-installed Mojo — any `def` that calls a raising function (e.g. `Python.import_module()`, `Path.read_text()`, `String.split()`, `assert_*`) needs explicit `raises`, and callers up the stack must also be `raises` (or wrap in `try`). |
| `owned` parameter keyword + `^` transfer | **Correction (empirical, C1):** `owned` keyword is removed. `def` params are **immutable references** by default — `^` transfer from a `def` param fails with "cannot transfer out of immutable reference". Use `.copy()` in constructors instead: `self.field = field.copy()`. |
| `mojo test` subcommand | **Correction (empirical, C1):** removed from this toolchain. Write each test file as a runnable with `def main() raises:` that calls every `test_*` function, then invoke via `mojo run -I src tests/test_foo.mojo`. |
| `mojo format --check` | **Correction (empirical, C1):** `--check` flag doesn't exist. Workaround: format into a temp copy and `diff` against real sources. See `scripts/format-check.sh`. |
| `String.split(sep)` returns `List[String]` | **Correction (empirical, C1):** returns `List[StringSlice[origin_of(text)]]` — views, not owned strings. Convert explicitly: `sliced.append(String(all_lines[i]))`. |
| `sys.argv()` return type | **Correction (empirical, C1):** returns `VariadicList[StringSlice[...]]`. Wrap elements in `String(args[i])` before passing to APIs expecting an owned `String`. |
| `alias X = ...` at module scope | **Correction (empirical, C3):** deprecated, use `comptime X = ...`. The compiler still accepts `alias` with a warning. |
| `Int(py_obj)` for PythonObject→Int | **Correction (empirical, C3):** the conversion constructor is keyword-only: `Int(py=py_obj)`. Bare `Int(py_obj)` fails with "missing required keyword-only argument 'py'". |
| Iterating a Python generator via `for x in gen` in Mojo | **Correction (empirical, C3):** truncates early on some streams (observed at chunk ~16 on MAX CLI output — likely interacts with tqdm progress lines containing `\r`). Workaround: keep the loop in Python and have Mojo call a single Python function that drives iteration itself. |
| `pixi run <task> <args>` arg forwarding | **Correction (empirical, C3):** pixi 0.67 does not forward trailing args to string tasks. Delegate to a shell script and invoke via `pixi run bash scripts/<name>.sh <args>`. |
| MAX on Apple GPU for text generation | **Correction (empirical, C3):** MAX 26.2 sampling graph uses a `topk` kernel that requires "external memory" — not supported on Apple Metal. On arm64, pin `--devices cpu`. Linux+CUDA is unaffected. |
| `PYTHONIOENCODING` for Python subprocess output containing non-ASCII | **Correction (empirical, C3):** set `PYTHONIOENCODING=utf-8` in the run wrapper so `sys.stdout.write(line)` doesn't crash on tqdm progress bars (U+2588 `█`). |
| "4 core tools: bash, read, write, edit" | pi-mono ships **7** built-in tools: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls` (`packages/coding-agent/src/core/tools/index.ts:110-194`). |
| "4 message variants: User/Assistant/System/Tool" | Runtime union is 3: `UserMessage | AssistantMessage | ToolResultMessage` (`packages/ai/src/types.ts:223`). System prompt is a string field on `Context`, not a message. |
| Structured output via logit biasing | MAX has grammar-constrained decoding (llguidance backend) but **GPU-only**. CPU fallback must rely on regex + retry-injection. |
| Mojo `print(msg, file=2)` for stderr | **Correction (empirical, C1):** Mojo's `print()` has no `file=` kwarg. stderr routing is a W-phase concern; for now use plain `print()` everywhere. |

**Honest framing:** this port is *Mojo-orchestrated, MAX-inferred, Python-glued*. The "pure Mojo" vision in the PRD is aspirational; current reality requires Python interop for MAX, Git, and TUI rendering. The plan treats Python interop as a first-class strategy, not a fallback.

---

## 1. Target architecture

Unified local process, three domains (matches PRD diagram):

```
┌──────────────────────────────────────────────────────────────────┐
│  Mojo process (single binary, no network)                        │
│                                                                  │
│  ┌───────────────┐   ┌───────────────┐   ┌──────────────────┐   │
│  │ Agent Runtime │──▶│ Tool Executor │   │ MAX Engine       │   │
│  │ (Mojo)        │◀──│ (Mojo stdlib) │   │ (Python interop) │   │
│  │               │   │               │   │                  │   │
│  │ AgentSession  │   │ subprocess    │   │ InferenceSession │   │
│  │ AgentLoop     │   │ pathlib/io    │   │ TextGenPipeline  │   │
│  │ SessionStore  │   │ ripgrep shell │   │ PagedKVCache     │   │
│  │ Context Build │   │ git via py    │   │ GGUF loader      │   │
│  └───────────────┘   └───────────────┘   └──────────────────┘   │
│          │                                        ▲             │
│          └────────── token stream ◀───────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

**Data pathway per turn:**
1. `AgentSession` composes `AgentContext` (system prompt + `AGENTS.md` + message history).
2. `convert_to_llm()` serializes `AgentMessage[]` into Llama-3 ChatML tokens.
3. `MaxInference` (Python interop wrapper) calls `pipeline.execute()` and yields tokens back into Mojo via an event queue.
4. Tool-call parser scans the stream for `<tool_call>` blocks; on hit, halts generation, dispatches to `ToolExecutor`.
5. Tool result is appended to the KV cache context; loop continues.

---

## 2. Scope matrix (pi-mono → Mojo)

| pi-mono package | Port status | Target |
|---|---|---|
| `packages/ai` (types, streaming, provider registry) | **Port subset** — types only; provider registry replaced by single MAX backend | `mojopi/ai/` |
| `packages/agent` (AgentSession, agent-loop, tools abstraction) | **Port fully** — core ReAct state machine | `mojopi/agent/` |
| `packages/coding-agent` (CLI, tools, sessions, extensions, modes) | **Port fully** (MVP: Interactive + Print modes; JSON/RPC deferred) | `mojopi/coding_agent/` |
| `packages/tui` | **Python interop via `textual`** for MVP; native Mojo TUI later | `mojopi/tui_py/` (Python shim) |
| `packages/mom` (Slack bot) | **Deferred** | — |
| `packages/pods` (vLLM remote pods) | **Out of scope** (local-only port) | — |
| `packages/web-ui` (Lit browser UI) | **Deferred**, rebuild later against Mojo agent's RPC mode | — |

---

## 3. Data model (Mojo structs/Variants)

Maps `packages/ai/src/types.ts:1-413` and `packages/agent/src/types.ts` to Mojo. Field names preserved for session-file backward compatibility.

```mojo
from utils.variant import Variant
from collections import List, Dict

struct TextContent(Copyable, Movable):
    var text: String

struct ImageContent(Copyable, Movable):
    var data: String          # base64
    var mime: String

struct ThinkingContent(Copyable, Movable):
    var text: String
    var redacted: Bool
    var signature: String

struct ToolCall(Copyable, Movable):
    var id: String
    var name: String
    var arguments: String     # raw JSON (validated at dispatch time)

alias AssistantBlock = Variant[TextContent, ThinkingContent, ToolCall]

struct UserMessage(Copyable, Movable):
    var content: List[Variant[TextContent, ImageContent]]
    var timestamp: Int64

struct AssistantMessage(Copyable, Movable):
    var content: List[AssistantBlock]
    var model: String
    var usage: Usage
    var stop_reason: StopReason
    var timestamp: Int64

struct ToolResultMessage(Copyable, Movable):
    var tool_call_id: String
    var tool_name: String
    var content: List[Variant[TextContent, ImageContent]]
    var is_error: Bool
    var timestamp: Int64

alias AgentMessage = Variant[UserMessage, AssistantMessage, ToolResultMessage]

struct AgentContext(Movable):
    var system_prompt: String
    var messages: List[AgentMessage]
    var tools: List[AgentTool]
```

**Session tree** (matches `packages/coding-agent/src/core/session-manager.ts:28-100` schema **v3**):

```mojo
alias SessionEntry = Variant[
    SessionHeader,          # type: "session",  v: 3, id, cwd, parentSession?
    MessageEntry,           # type: "message",  id, parentId, message
    ThinkingLevelChange,    # type: "thinking_level_change"
    ModelChange,            # type: "model_change"
    CompactionEntry,        # type: "compaction"
    BranchSummaryEntry,     # type: "branch_summary"
    CustomEntry,            # type: "custom"          (extension state)
    CustomMessageEntry,     # type: "custom_message"  (injected message)
]
```

Every entry owns `id` + `parentId` → tree traversal by walking parent chain (matches TS logic at `session-manager.ts:300+`).

---

## 4. Phased roadmap — crawl / walk / run

**Nine phases** in three tiers. Each tier is a *meta-gate*: Walk doesn't start until every Crawl phase lands; Run doesn't start until every Walk phase lands. Within a tier, phases are sequential unless noted.

Naming: `Cx` = Crawl tier, `Wx` = Walk tier, `Rx` = Run tier.

| Tier | Phase | Name | Weeks | One-line goal |
|---|---|---|---|---|
| C | C1 | Crawl.Crawl | 1 | Scaffolding: Mojo + MAX + Python interop build green |
| C | C2 | Crawl.Walk | 2 | Three independent slices: types, one tool, MAX load |
| C | C3 | Crawl.Run | 3–4 | One-shot: `mojopi -p "hello"` streams tokens to stdout |
| W | W1 | Walk.Crawl | 5–7 | Session store + context loader + **embedded MAX pipeline** |
| W | W2 | Walk.Walk | 7–9 | 7 tools + ReAct loop + CLI (TUI non-blocking) |
| W | W3 | Walk.Run | 9–11 | Compaction + steering + skills — long sessions survive |
| R | R1 | Run.Crawl | 12–13 | Python extension API + print-mode polish + migration doc |
| R | R2 | Run.Walk | 14–15 | Hit NFR targets (TTFT/throughput/RSS); GPU structured output |
| R | R3 | Run.Run | 16–17 | Distribution + JSON/RPC modes + v1.0 release |

---

### Tier C — CRAWL: prove the stack works (weeks 1–4)

Crawl proves one thing: Mojo + MAX + Python interop + pi-mono's data model coexist in a single binary that takes stdin and emits tokens. No tool loop, no session persistence, no UI.

#### C1 — Crawl.Crawl: scaffolding & smoke (week 1)
**Goal:** repo builds, Python interop verified, CI green on two OSes.
- [ ] `pixi init mojopi` with Mojo v26.2 + MAX SDK + CPython 3.12 pinned.
- [ ] Repo skeleton matching §1 (empty modules with `# TODO` comments acceptable).
- [ ] GitHub Actions matrix: `macos-14` + `ubuntu-24.04`. `mojo test` + format check.
- [ ] Smoke test: Mojo binary imports `max` from Python, prints version, exits 0.

**Gate:** `pixi run test` green on both OSes.

#### C2 — Crawl.Walk: types + one tool + MAX load (week 2)
**Goal:** three independent vertical slices work in isolation.
- [ ] Data types (no Variants yet — use tagged unions): `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `TextContent`, `ToolCall`.
- [ ] One tool: `read` only. `pathlib.Path` + `io`. Unit test: reads a 50-line fixture with offset/limit.
- [ ] MAX: `max_brain/pipeline.py` can build a `TextGenerationPipeline` for Llama-3.1-8B-Q4_K_M and report config. No generation yet.

**Gate:** three unit tests pass — data round-trip, read-tool fixture, pipeline constructs without error.

#### C3 — Crawl.Run: one-shot end-to-end (weeks 3–4)
**Goal:** `mojopi -p "what is 2+2"` prints an answer.
- [ ] Prompt formatter: hard-coded Llama-3 ChatML template (single-turn only).
- [ ] MAX generation: `pipeline.generate()` streams tokens to stdout.
- [ ] No tools wired, no session file, no agent loop, no context files.

**Gate:** demo: user runs `mojopi -p "what is 2+2"`, sees `4` stream. TTFT measured but not gated.

---

### Crawl → Walk: learnings applied

Before executing Walk, here's what Crawl taught us and how it reshapes the plan:

| Learning from Crawl | How Walk adapts |
|---|---|
| Mojo API churn is real: 14 empirical corrections logged in §0 (`std.*` prefix, explicit `raises`, `.copy()` on def params, `Int(py=…)`, `alias→comptime`, etc.). | Every Walk agent prompt explicitly references §0 corrections. Budget 20% of each phase for newly-discovered churn. |
| **`max generate` subprocess is ~11 s startup + graph compile per call.** Unusable for interactive iteration. | **Embedded `TextGenerationPipeline` is now a W1 deliverable** (moved up from W2). Load model once, drive many turns. Every subsequent phase assumes fast inference. |
| Mojo iterating a Python generator (`for x in gen`) truncates early around the 16th chunk (tqdm `\r` interaction). | **Banned pattern.** Token streaming keeps the iteration loop in Python; Mojo calls a single Python function that handles the whole drive. See `pipeline.run_one_shot` for the template. |
| Apple Metal GPU blocked by MAX 26.2 topk kernel constraint. | On arm64, pin `--devices cpu` and accept ~15 tok/s throughput. Perf targets (TTFT <150 ms, >30 tok/s) remain an R2 concern, gated on MAX upstream fixes or Linux+CUDA CI. |
| Mojo `def` params are immutable refs — `^` transfer fails, must use `.copy()`. | W1 session structs (7 entry types × many fields) inherit this discipline. Agent prompts call it out explicitly. |
| pixi 0.67 does not forward trailing args to string tasks. | All CLI flows go through `bash scripts/<name>.sh` wrappers. No more `pixi run foo -- --flag` patterns. |
| 6-agent parallelism worked cleanly with file-ownership boundaries. | Walk continues with 3–6 agent parallel dispatches per phase, same hand-off protocol (§5). |
| Empirical correction surface is deeper than docs. | Every phase ends with a "PLAN §0 delta" note — we keep logging corrections so future agents start with current truth. |

---

### Tier W — WALK: behavioral parity with TS `pi` (weeks 5–11)

Walk's goal: a user with an existing `~/.pi/agent/sessions/` directory opens sessions in `mojopi`, has a conversation that *works* — same tools, same AGENTS.md handling, same session tree. Not fast yet, not pretty yet. Timeline slipped by ~1 week vs. the original plan to absorb the embedded-pipeline work now inside W1.

#### W1 — Walk.Crawl: persistence + embedded pipeline (weeks 5–7)
**Goal:** existing pi sessions are readable, AGENTS.md is composable, and we have a model-load-once pipeline so everything else iterates fast.

Three slices, parallelizable across 3 agents:

- **Session store** (port of `packages/coding-agent/src/core/session-manager.ts`):
  - [ ] JSONL reader/writer for all 7 v3 entry types: `session`, `message`, `thinking_level_change`, `model_change`, `compaction`, `branch_summary`, `custom`, `custom_message`.
  - [ ] Session tree builder: `get_leaf_branches()`, `resolve_path(leaf_id) → List[AgentMessage]`, fork + label.
  - [ ] `--session <uuid-prefix|path>` resolver — port of `main.ts:147-180`.
  - [ ] Every struct constructor uses `.copy()` discipline (per §0).

- **Context loader** (port of `resource-loader.ts:58-75` + `system-prompt.ts:28-80`):
  - [ ] Walk cwd→root for `AGENTS.md` / `CLAUDE.md`. Concatenate matches.
  - [ ] `.pi/SYSTEM.md` + `.pi/APPEND_SYSTEM.md` project overrides.
  - [ ] Global `~/.pi/agent/AGENTS.md`; `--no-context-files` toggle.
  - [ ] System prompt builder: tool descriptions + context files + date + cwd.

- **Embedded MAX pipeline** (replaces the C3 `max generate` subprocess):
  - [ ] Python module: build `TextGenerationPipeline(PipelineConfig(model=..., ...))` once at startup.
  - [ ] `generate(messages, max_new_tokens)` → streams tokens into a shared queue.
  - [ ] Mojo side calls a single Python function that drives iteration (never loops over a Python generator from Mojo).
  - [ ] Token-level streaming callback, not line-level.
  - [ ] Target: first token < 3 s after process start (model pre-loaded), <100 ms per subsequent turn-start.

**Gate:**
- All 7 JSONL entry types round-trip cleanly on a corpus of ≥10 real pi-mono sessions. TS `pi` opens mojopi-written session files without error.
- `mojopi -p "…"` using the embedded pipeline produces the same answer as Crawl's C3 demo but with <100 ms turn-to-turn latency on a warm model.
- 22/22 Crawl tests still green; new W1 tests bring the suite to ≥35.

**Relaxations vs. original Walk.Crawl:**
- "≥50 real sessions" → "≥10 sessions covering all 7 entry types." Real corpora this early don't have coverage; relaxing unblocks the phase.
- Non-goal: image/binary message blocks (deferred to W3 if needed).

#### W2 — Walk.Walk: 7 tools + ReAct loop + CLI (weeks 7–9)
**Goal:** core agent works end-to-end on a scripted multi-turn task.

Four parallel streams, ~5 agents:

- **Tool parity** (2 agents, split):
  - Agent A: `read` (extend from C2), `grep`, `find`, `ls` — read-only tools.
  - Agent B: `bash`, `edit`, `write` — mutating tools.
  - Each tool: ≥20 golden fixtures (originally 30+; relaxed). Total ≥140 fixtures.
  - Python shim isolation: any tool using Python libs (diff-match-patch, Pillow) lives behind a Mojo trait, swappable to native later.
  - Cancellation via abort flag; `bash` forwards SIGTERM to child tree.

- **ReAct loop** (1 agent):
  - Port of `agent-loop.ts:155-331` — `run_loop()` + `stream_assistant_response()`.
  - Sequential tool dispatch only; parallel deferred to R3.
  - **Tool-call extraction from token stream** — operate on tokens, not lines (lesson from Crawl). Detect `<tool_call>…</tool_call>` or Llama-3.1 native tool-call tokens.
  - Retry-on-malformed loop: max 3 attempts, inject syntax-error tool result back into context.

- **CLI arg parser** (1 agent):
  - Port of `cli/args.ts`. All flags: `--model`, `--tools`, `--system-prompt`, `--no-*`, etc.
  - Built on top of W1's `scripts/run.sh` wrapper (pixi arg-forwarding is still broken; we stay on the workaround).

- **TUI** (1 agent, deferred sub-task):
  - Python `textual` shim for interactive mode. Input box + streaming pane + tool-call collapsible.
  - **Not on the gate.** W2 gate runs in `-p` print mode. TUI lands in W2 or slips to W3 without blocking.

**Gate:** A 20-turn scripted session ("analyze this repo, propose a refactor, apply changes, run tests") completes in `-p` mode without divergence from the TS reference on deterministic inputs. RSS stays under 250 MB excl. weights/KV.

**Timing note:** at 15 tok/s on CPU, 20 turns × ~100 tok ≈ 130 s of generation alone. Budget 15 min per gate run including tool execution; expect 2–4 gate runs before landing.

#### W3 — Walk.Run: compaction + steering + skills (weeks 9–11)
**Goal:** long sessions survive; the agent can be interrupted and gracefully correct course.

- [ ] **Context compaction**: trigger at 75% of window; secondary embedded-pipeline call summarizes oldest N tool-call/result pairs; write `CompactionEntry` preserving branching (the original tree stays intact; compaction is a new node).
- [ ] **Steering messages**: mid-turn user interrupt queue. Producer runs in Python (keyboard or file-watcher); Mojo polls via a single-function call each turn boundary. **No Mojo async.**
- [ ] **Follow-up queue**: same Python-producer pattern, polled at the `agent-loop.ts:220` equivalent.
- [ ] **Skills**: `.pi/skills/*.md` loader (markdown with YAML frontmatter) via Python interop. Conditional inclusion gated by `read` tool availability.
- [ ] **Abort/cancellation**: abort flag threaded through every call; on abort, flush partial assistant message with `stopReason: "aborted"` and finalize the session entry.
- [ ] **`beforeToolCall` / `afterToolCall`** hooks as Mojo trait methods — sets up the Run-tier extension API.

**Gate:** a 100-turn autonomous session runs to completion. RSS < 250 MB excl. weights/KV (relaxed from original 200 MB — the W1 embedded pipeline adds ~50 MB of tokenizer + scheduler overhead that's the cost of fast iteration). Context compaction fires at least once during the run.

**Timing note:** 100 turns × ~100 tok = 10 min of generation on CPU plus tool time. Plan overnight CI runs for this gate.

---

### Walk → Run: learnings applied

| Learning from Walk | How Run adapts |
|---|---|
| Python interop is permanent — MAX, tools, TUI all use Python. | R1 extension API is Python-native from the start. No Mojo trait wrappers needed. |
| TUI deferred from W2. | TUI is now the first R1 item. No extension API ships without a working TUI. |
| Hook system in place (W3 agent.hooks). | R1 extension API builds on hooks — no second event bus. |
| MAX TextGenerationPipeline config bug blocks fully embedded pipeline. | R2 first task is to diagnose and fix this. Use subprocess fallback in the meantime. |
| Mojo 0.26.2 correction surface is stable (14 entries in §0). | R tier agents inherit all §0 corrections in their prompts. No new corrections expected unless MAX bumps again. |
| Tool dispatch is Python-heavy (thin Mojo wrappers over Python helpers). | Accept this. "Pure Mojo tools" is aspirational. |
| Session v3 format maintained. TS pi compatibility met. | R3 ships with session v3 as the stable format. Schema evolution goes through RFC. |

---

### Tier R — RUN: shippable to real users (weeks 12–17)

Run's goal: `mojopi` is something a pi-mono user installs and uses daily instead of `pi`.

#### R1 — Run.Crawl: TUI + extensions + print polish + docs (weeks 12–14)
**Goal:** interactive TUI works; users can bring their own tools; `-p` mode is production-quality.

- [ ] **TUI (deferred from W2)**: Python `textual` shim. Input box + streaming pane + tool-call collapsible. Wired into the W3 steering queue for keyboard interrupt. Test: basic session renders in textual without hang.
- [ ] Python extension API: `register_tool`, `register_command`, `on(event)`. Built on top of the W3 hooks framework (`agent.hooks`). Discovery from `~/.pi/agent/extensions/` + `.pi/extensions/` + `--extension`.
- [ ] Event taxonomy parity with `extensions/types.ts`: `tool_call`, `message_start`, `message_end`, `before_agent_start`, `before_compact`, `custom_event`.
- [ ] Custom tools: Python callables wrapped in a Mojo `AgentTool` adapter (the `AgentTool` struct already exists in `src/agent/types.mojo`).
- [ ] Print mode (`-p`) hardening: stdin piping, `@file` arguments, exit codes, `--system-prompt` / `--append-system-prompt`.
- [ ] Migration doc: TS extension → Python extension, side-by-side for 3 common examples.

**Note:** The hooks framework (W3 `agent.hooks`) is the implementation substrate for the extension API. R1 adds the discovery + registration UX on top.

**Gate:** a real pi-mono user ports one of their extensions and runs it against `mojopi -p` in < 30 min.

#### R2 — Run.Walk: benchmarks + GPU path + perf hardening (weeks 14–15)
**Goal:** hit NFR targets. Stop gaslighting ourselves about perf.

- [ ] Benchmark suite in CI: TTFT, throughput, RSS, cold start. Nightly on macOS M-series.
- [ ] Fix the `get_or_create_pipeline()` MAX config bug: the TextGenerationPipeline constructor rejects keyword args in some invocations — investigate the correct MAX Python API for 2026, update pipeline.py accordingly.
- [ ] Structured-output path: `--enable-structured-output` on GPU builds with JSON-Schema grammar for tool calls. GPU-only; CPU fallback stays with regex + retry.
- [ ] Python GIL profiling: identify hot spots in the MAX call path; consider a dedicated Python thread for MAX calls if GIL contention is measurable.
- [ ] Fix anything > 20% off target.

**NFR targets (unchanged from §6):** TTFT < 150 ms (M1 Max), throughput > 30 tok/s (Llama-3.1-8B Q4_K_M), RSS < 100 MB excl. weights/KV, cold start < 50 ms excl. model load.

**Realistic note:** at 15 tok/s on Apple Silicon CPU (MAX 26.2 with topk GPU block), the throughput target requires either MAX upstream fixes or Linux + CUDA. This is tracked as Risk R4 in §7. The Apple CPU path targets best-effort quality; NFR gating is Linux + CUDA CI.

#### R3 — Run.Run: distribution + JSON/RPC + v1.0 (weeks 15–17)
**Goal:** v1.0 shipped.

- [ ] `pixi global install mojopi` from a public conda channel (or pixi.sh global).
- [ ] `--mode json` (streaming JSONL to stdout). Each token + tool call + final answer as a JSONL event.
- [ ] `--mode rpc` (JSONL-framed RPC over stdin/stdout for editor integration — VS Code extension target).
- [ ] Parallel tool dispatch (read-only tools only: read, grep, find, ls). Use Python `threading.Thread` pool (not Mojo async — Risk R2 in §7).
- [ ] Release notes, install doc, `AGENTS.md` doc, extension API reference.
- [ ] Mojo version pin: pin pixi.toml to a specific Mojo/MAX build for the v1.0 release. Log corrections §0 for that version. Run the full test suite against it before tagging.

**Gate:** v1.0 tag cut. External user completes README quickstart on a clean machine without help.

---

## 5. Development: the 8-agent pool

~43k LOC of TS → Mojo + Python is too much for one person or one agent. A human lead orchestrates up to **8 specialized Claude sub-agents** working concurrently. Each agent owns a domain, has its own test suite, and produces merge-ready PRs.

### Orchestration model
- Lead runs a daily planning pass, dispatches agents with narrow, self-contained prompts (include file paths + line numbers, per the "never delegate understanding" rule).
- Agents run in **parallel** when their domains don't overlap (most days).
- Lead reviews PRs, resolves cross-domain conflicts, decides phase-gate readiness.
- No agent writes to another agent's module without an explicit hand-off.

### Agent roster

| # | Agent | Domain | Primary phases | Input → Output |
|---|---|---|---|---|
| 1 | **Mojo Idioms** | Language churn, TS→Mojo translation, `def`/ownership rules, Variant dispatch | C1, C2, W2, W3 | TS module + spec → Mojo port + unit tests |
| 2 | **MAX Integration** | Python interop, `max.pipelines`, `PagedKVCacheManager`, GGUF loading, token streaming | C2, C3, R2 | Model requirements → `max_brain/*.py` + Mojo wrappers |
| 3 | **Tool Parity** | The 7 tools, fixture corpus, TS-vs-Mojo byte-equality | C2 (`read`), W2 (all others) | TS tool source → Mojo port + ≥30 golden fixtures each |
| 4 | **Session & Context** | JSONL schema v3, tree walking, `AGENTS.md` discovery, compaction | W1, W3 | Real session corpus → parser + writer + compactor |
| 5 | **ReAct Loop** | `agent-loop.ts` port, streaming event bus, steering/follow-up queues, retry loop | W2, W3 | `agent-loop.ts:155-331` → `AgentLoop` struct + state tests |
| 6 | **TUI / UX** | `textual` Python shim, streaming render, keyboard routing, print-mode polish | W2, R1 | Screen specs → Python TUI + Mojo bridge |
| 7 | **Bench & CI** | pixi config, GitHub Actions matrix, TTFT/throughput/RSS benchmarks, regression alerts | C1, R2, R3 | NFR targets → CI jobs + dashboards |
| 8 | **Extensions & DevEx** | Python extension API, migration guide, install UX, docs | R1, R3 | Extension examples → API + docs |

### Concurrency per tier

- **Crawl (weeks 1–4):** 3 agents concurrent — #1 Mojo Idioms, #2 MAX Integration, #7 Bench & CI. #3 Tool Parity joins at C2 for `read`.
- **Walk (weeks 5–10):** all 8 active. #4 Session & Context + #5 ReAct Loop + #6 TUI do the heavy lifting; #3 Tool Parity ports the remaining 6 tools in parallel; others support.
- **Run (weeks 11–16):** #8 Extensions leads R1; #2 MAX + #7 Bench lead R2; #6 TUI + #8 Extensions + #1 Mojo Idioms lead R3.

### Hand-off discipline

When an agent finishes a unit, the hand-off PR includes:
1. Green tests for the changed surface.
2. One-paragraph summary of what changed and why.
3. Any new public APIs the next agent must consume (+ example usage).
4. Explicit list of deferred work (added to §8 open questions).

The lead rejects PRs that skip this protocol. This is how 8 parallel agents stay coherent over 16 weeks.

### When to spawn fewer agents

Not every phase needs 8 agents. Guide:
- **Solo work (1 agent):** C1 scaffolding, C3 one-shot demo, hand-off-heavy weeks.
- **Pair (2 agents):** most of Crawl, R1 docs, R3 release.
- **Small squad (3–5):** typical Walk week.
- **Full 8:** peak Walk weeks when tools + loop + TUI all progress in parallel, and at R2 benchmark-hardening when every domain needs perf attention.

Over-dispatching agents on easy work is a failure mode — wastes context, generates PR noise. Dispatch to the actual blocker.

---

## 6. Non-functional targets

| Metric | Target | Validated in |
|---|---|---|
| TTFT | < 150 ms on M1 Max, < 200 ms on A10G | R2 |
| Throughput | > 30 tok/s Llama-3.1-8B Q4_K_M | R2 |
| Base RSS (excl. weights/KV) | < 100 MB | R2 |
| Cold start to prompt | < 50 ms (excl. model load) | R2 |
| Hardware coverage | Apple M-series + NVIDIA A10G/H100 via MAX | R3 |

Model load time (separate from cold start): target < 10 s for Llama-3.1-8B-Q4_K_M on M1 Max; mmap from local GGUF cache.

---

## 7. Risks & mitigations

Grounded in the SDK verification, not generic.

### R1 — MAX is Python-first; "Mojo-native" is marketing
**Impact:** every MAX call goes through CPython interop. GIL contention during async tool execution is possible.
**Mitigation:** keep MAX calls on a dedicated Python thread (`create_task` + a single interpreter-owned `asyncio` loop). Tool execution stays pure Mojo. Re-evaluate when Mojo `max.engine` API is re-released post-open-source.

### R2 — Mojo async model is Phase 2
**Impact:** `Task`/`Coroutine` ownership rules (non-copyable, must `^` transfer) produce confusing compile errors; language spec still churning.
**Mitigation:** minimize `async def`. Core loop is sequential. Use async only for (a) steering-message polling, (b) TUI render tick, (c) token-stream bridge. Prefer `TaskGroup.create_task` over hand-rolled coroutine juggling. Pin Mojo version per release; update in explicit sprints (a Mojo-Idioms-agent task).

### R3 — `fn` → `def` migration churn
**Impact:** PRD code samples use `fn`; current Mojo deprecates it.
**Mitigation:** use `def` everywhere in new code. Write a `pixi run lint-mojo` rule that flags `fn ` (with space) as error.

### R4 — Structured output is GPU-only
**Impact:** CPU-only deployments (cheap Linux VMs, Apple systems without Metal accel) can't rely on grammar-constrained decoding.
**Mitigation:** regex-based tool-call extraction + retry-injection loop (W2), with GPU grammar-constrained decoding added in R2. Document that structured-output is a GPU optimization, not a requirement.

### R5 — GGUF/quantization compat drift
**Impact:** `bfloat16` fails on some CPU fallbacks; MAX changelog shows frequent KV-cache flag renames (e.g., `--host-kvcache-swap-space-gb` removed in v26.3).
**Mitigation:** pin MAX version per release. Integration test: load + 10-token generate for each supported model in CI. Changelog-watch: release gate includes "diff MAX changelog since last release" step.

### R6 — TUI via Python `textual` interop
**Impact:** rendering latency and keyboard-event round-trip through Python may feel sluggish vs. TS raw-ANSI implementation.
**Mitigation:** accept the perf hit for W2; measure input→render latency in R2. If > 50 ms p99, escalate: either (a) port TUI to native Mojo using raw ANSI (follows `packages/tui/src/terminal.ts` pattern), or (b) ship a bare-bones native-Mojo line editor for the `--mode print` path, keep textual for interactive only.

### R7 — jiti ↔ Python extension API mismatch
**Impact:** existing pi-mono extensions are TypeScript; users must rewrite for the Mojo port.
**Mitigation:** this is unavoidable. Ship a **migration doc** with side-by-side TS → Python examples for the top N existing extensions. Keep the extension API surface (`register_tool`, `register_command`, `on(event)`) shape-identical to minimize cognitive load.

### R8 — Session-file schema forward compat
**Impact:** if the Mojo port writes a v4 schema, legacy `pi` can't read it.
**Mitigation:** v1 of the port is **read/write schema v3 only**. Any schema evolution goes through an RFC. Integration test: TS `pi` opens Mojo-written sessions without error.

### R9 — No stable Mojo packaging / build story
**Impact:** `mojo package` exists but the packaging ecosystem is Phase 2; distribution story is weak.
**Mitigation:** for v1 ship via `pixi global install mojopi` from a private conda channel. Defer "single static binary" ambition until Mojo 1.0 cross-compilation stabilizes.

### R10 — Coding-agent is 129 TS files, ~43k LOC
**Impact:** this is not a weekend rewrite. The 16-week roadmap assumes 1 human lead orchestrating up to 8 sub-agents (§5). With fewer agents or without strict phase gates, slip to 24+ weeks is realistic.
**Mitigation:** enforce the meta-gates between tiers — no Walk work until all Crawl phases land, no Run work until all Walk phases land. Tier gates are stricter than intra-tier gates: slipping one phase inside Walk is acceptable; crossing into Run without all Walk gates is not.

---

## 8. Open questions (decide before Tier W)

1. **Model distribution:** ship with a default model pre-fetched, or require `mojopi model pull llama-3.1-8b-q4_k_m` first-run? Implication: binary size vs. first-run UX.
2. **Tokenizer source of truth:** HF tokenizer via `transformers` (Python) vs. MAX's built-in tokenizer — which wins on correctness for Llama-3 chat template?
3. **Remote fallback:** should `mojopi` optionally call a remote MAX endpoint (over HTTP) when local hardware is insufficient? The PRD says "local only" but some devices genuinely can't run an 8B model. Leaning **no** for v1 to avoid reintroducing the very network dependency this port exists to remove.
4. **License compatibility:** pi-mono is MIT. Confirm MAX SDK redistribution terms before shipping a distributable build.
5. **Telemetry:** zero telemetry in v1, or opt-in perf metrics for benchmark collection? Recommend **zero** — aligns with the "local-first privacy" narrative.
6. **Multi-model switching mid-session** (`/model` slash command in TS `pi`): does reloading a different GGUF invalidate the paged KV cache? Almost certainly yes. Plan: drop the cache and re-prefill from message history. Document as a ~5-10s operation.

---

## 9. What a v1 ship looks like

- Binary `mojopi` (installed via pixi) running on macOS (Apple Silicon) + Linux x86/CUDA.
- Bundled Llama-3.1-8B-Instruct-Q4_K_M default; pull others via CLI.
- All 7 built-in tools at TS parity on fixture suite.
- Interactive TUI + `-p` print mode. JSON/RPC modes deferred to v1.1.
- `.pi/AGENTS.md`, `.pi/SYSTEM.md`, `.pi/skills/`, `.pi/extensions/` all respected.
- Python-based extension API with migration guide.
- Session format schema v3 — reads/writes existing pi-mono session files losslessly.
- Benchmarks in CI: TTFT, throughput, RSS, cold start.

**Non-goals for v1:** mom (Slack), pods (vLLM), web-ui, `--mode json`, `--mode rpc`, Skills auto-install from git/npm, pi package registry, web-search tool, image generation, Kitty keyboard protocol in TUI.

---

## 10. First concrete tasks (C1 sprint)

These five tasks land phase C1. Dispatch agents #1 (Mojo Idioms), #2 (MAX Integration), #7 (Bench & CI) in parallel.

1. **[#7]** Create `mojopi/pixi.toml` with Mojo 26.2 + MAX SDK + CPython 3.12 pinned.
2. **[#1]** Scaffold the repo skeleton from §1 (empty modules, `# TODO` comments acceptable).
3. **[#7]** One GitHub Actions job running `mojo test tests/` on `macos-14` + `ubuntu-24.04`.
4. **[#2]** Minimal Mojo program: `from python import Python`, import `max`, print `max.__version__`, exit 0.
5. **[#1]** `mojo test` fixture: one passing test asserts `1 + 1 == 2`, to prove the test harness runs in CI.

Each is independently landable. When all five are green on both OSes, C1's gate is met and C2 can begin.
