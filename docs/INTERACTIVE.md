# Interactive mode

Running `mojopi` with no `-p` flag drops you into an interactive REPL backed by
the full ReAct agent loop. Every line you type is sent to the agent, which can
call the 7 built-in tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`)
to inspect and modify the local filesystem.

## Launch

```bash
pixi run run                    # default model (Llama-3.1-8B GGUF)
pixi run run -- --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit
```

## Slash commands

```
/help       show commands
/version    print mojopi version + MAX version
/clear      clear the screen
/exit       exit the REPL
/quit       same as /exit
```

Anything else is sent to the agent as a user message.

## What the agent can do

For each user turn, mojopi:

1. Assembles the system prompt (tool docs + AGENTS.md / CLAUDE.md + date/cwd)
2. Sends the formatted ChatML to the model via MLX Metal (or MAX on Linux)
3. Parses any `<tool_call>…</tool_call>` blocks from the response
4. Executes the tools and feeds results back to the model
5. Loops up to 10 tool-call rounds, or until the model answers in plain text

This is the same loop pi-mono runs — see `src/agent/loop.mojo` for the
implementation.

## Interrupting

Ctrl-C pushes an abort through the W3 steering queue. The agent checks the
abort flag before each generation turn and before each tool call, so a
long-running response stops at the next checkpoint.

## Session resume (future)

`--session <uuid-prefix>` wires through to the CliArgs parser but is not yet
connected to the session store in interactive mode. The JSONL session format
(W1) is ready; the R1 follow-up hooks it up.

## Context files

mojopi walks up from the cwd looking for `AGENTS.md` / `CLAUDE.md` at every
level. All matches are concatenated into the system prompt. Disable with
`--no-context-files`.

Project-level overrides:

- `.pi/SYSTEM.md` — replaces the default preamble
- `.pi/APPEND_SYSTEM.md` — appended to the prompt
- `~/.pi/agent/AGENTS.md` — global context included everywhere

## Extensions

Drop Python files in `~/.pi/agent/extensions/*.py` or `.pi/extensions/*.py` to
register custom tools, commands, or event handlers. See [EXTENSIONS.md](EXTENSIONS.md).

## Output mode

In interactive mode, output is always human-readable print mode. Use
`mojopi -p '...' --mode json` for machine-readable JSONL, or `--mode rpc` for
LSP-style JSONL-framed RPC for editor integrations.
