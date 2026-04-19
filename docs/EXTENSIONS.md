# Extension Migration Guide: TypeScript → Python

## Overview

pi-mono extensions were written in TypeScript using the types defined in `extensions/types.ts`.
The extension API exposed a `picoAI` object with three main methods: `register` (lifecycle hook),
`on` (event listener), and `registerTool` (add a custom tool to the agent).

mojopi extensions are plain Python files. They are discovered automatically from:
- `~/.pi/agent/extensions/*.py` — global, loaded for every project
- `.pi/extensions/*.py` — project-local, loaded when running from that directory

The Python API lives in three modules:

| Module | Purpose |
|---|---|
| `coding_agent.extensions.registry` | Register tools and commands |
| `coding_agent.extensions.events` | Subscribe to agent lifecycle events |
| `coding_agent.extensions.loader` | Auto-discovery and explicit loading |

---

## Quick comparison table

| Concept | TypeScript (pi-mono) | Python (mojopi) |
|---|---|---|
| Register tool | `picoAI.registerTool(name, schema, fn)` | `register_tool(name, fn, description, schema_json)` |
| Listen to events | `picoAI.on("tool_call", handler)` | `on(TOOL_CALL, handler)` from `coding_agent.extensions.events` |
| Register command | `picoAI.registerCommand(name, fn)` | `register_command(name, fn)` from `coding_agent.extensions.registry` |
| Event payload | `{type, data}` | `EventPayload(event_type, data: dict)` |
| Discovery | `~/.pi/agent/extensions/*.ts` | `~/.pi/agent/extensions/*.py` |

---

## Example 1: Custom read-only tool

**TypeScript (pi-mono)**

```typescript
// ~/.pi/agent/extensions/my_tool.ts
picoAI.registerTool("fetch_weather", {
  description: "Fetch current weather for a city",
  input_schema: { city: { type: "string" } }
}, async ({ city }) => {
  return `Weather in ${city}: sunny, 22°C`;
});
```

**Python (mojopi)**

```python
# ~/.pi/agent/extensions/my_tool.py
from coding_agent.extensions.registry import register_tool

def fetch_weather(city: str) -> str:
    return f"Weather in {city}: sunny, 22°C"

register_tool(
    "fetch_weather",
    fetch_weather,
    description="Fetch current weather for a city",
    schema_json='{"city": {"type": "string"}}'
)
```

Key differences:
- The function is defined separately and passed to `register_tool` — no anonymous function required.
- `schema_json` is a JSON string (not a dict). Match the shape from the TypeScript `input_schema`.
- The function is synchronous. `async def` works too if you need it, but most tool logic does not.

---

## Example 2: Event listener (log every tool call)

**TypeScript (pi-mono)**

```typescript
picoAI.on("tool_call", ({ data }) => {
  console.log(`[audit] tool: ${data.name}`);
});
```

**Python (mojopi)**

```python
# ~/.pi/agent/extensions/audit.py
from coding_agent.extensions.events import on, TOOL_CALL

def on_tool_call(payload):
    print(f"[audit] tool: {payload.data.get('name', '?')}")

on(TOOL_CALL, on_tool_call)
```

Available event constants (imported from `coding_agent.extensions.events`):

| Constant | Fires when |
|---|---|
| `TOOL_CALL` | A tool is about to be dispatched |
| `TOOL_RESULT` | A tool has returned a result |
| `TURN_START` | A new ReAct turn begins |
| `TURN_END` | A ReAct turn completes |
| `SESSION_START` | The agent session starts |
| `SESSION_END` | The agent session ends |

Each handler receives an `EventPayload` with:
- `payload.event_type` — the event constant that fired
- `payload.data` — a `dict` with event-specific fields (e.g. `name`, `args`, `result`)

---

## Example 3: register_command (slash command equivalent)

**TypeScript (pi-mono)**

```typescript
picoAI.registerCommand("clear-cache", async () => {
  clearMyCache();
  return "Cache cleared";
});
```

**Python (mojopi)**

```python
# ~/.pi/agent/extensions/my_commands.py
from coding_agent.extensions.registry import register_command

def clear_cache():
    # your cache clearing logic
    return "Cache cleared"

register_command("clear-cache", clear_cache)
```

Registered commands are available in the TUI as `/clear-cache` (R1+). When invoked, the return
value is printed to the session output.

---

## Loading your extension

Extensions are auto-loaded from:

```
~/.pi/agent/extensions/*.py      # global (all projects)
.pi/extensions/*.py              # project-local
```

Or explicitly via CLI:

```
mojopi --extension /path/to/my_ext.py -p "use my tool"
```

Loading happens once at agent startup, before the first turn. All `register_tool`,
`register_command`, and `on` calls at module top-level are executed during this load phase.

If an extension raises an exception during load, mojopi logs the error and continues — the
remaining extensions and built-in tools are unaffected.

---

## API reference

### `coding_agent.extensions.registry`

| Symbol | Signature | Description |
|---|---|---|
| `register_tool` | `(name: str, fn: Callable, *, description: str, schema_json: str) -> None` | Register a callable as an agent tool. `schema_json` is a JSON string describing the input parameters. |
| `register_command` | `(name: str, fn: Callable) -> None` | Register a slash command. `name` must not include the leading `/`. |
| `get_tools` | `() -> list[ToolEntry]` | Return all registered extension tools (used internally by the dispatcher). |
| `get_commands` | `() -> dict[str, Callable]` | Return all registered commands keyed by name. |

### `coding_agent.extensions.events`

| Symbol | Kind | Description |
|---|---|---|
| `on` | `(event: str, handler: Callable[[EventPayload], None]) -> None` | Subscribe `handler` to `event`. |
| `emit` | `(event: str, data: dict) -> None` | Fire an event (used internally by the agent loop). |
| `TOOL_CALL` | `str` constant | Event fired before a tool is dispatched. |
| `TOOL_RESULT` | `str` constant | Event fired after a tool returns. |
| `TURN_START` | `str` constant | Event fired at the start of each ReAct turn. |
| `TURN_END` | `str` constant | Event fired at the end of each ReAct turn. |
| `SESSION_START` | `str` constant | Event fired once when the session opens. |
| `SESSION_END` | `str` constant | Event fired once when the session closes. |
| `EventPayload` | `dataclass` | `event_type: str`, `data: dict` |

### `coding_agent.extensions.loader`

| Symbol | Signature | Description |
|---|---|---|
| `load_extensions` | `(paths: list[str]) -> None` | Explicitly load extension files by path. Called automatically at startup. |
| `discover_extensions` | `() -> list[str]` | Return discovered extension paths from global and project-local directories. |
