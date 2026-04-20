"""Thin Python helper to build a complete system prompt from cwd.

Called from Mojo main.mojo to assemble tool descriptions + AGENTS.md context
+ date + cwd into a single system-prompt string.
"""
from __future__ import annotations
import os
from datetime import date

from coding_agent.context.loader import compose_context

TOOL_DESCRIPTIONS = """Available tools (emit as <tool_call>{"name": "...", "arguments": {...}}</tool_call>):

- read       Read a file. args: {"path": str}
- write      Write a file. args: {"path": str, "content": str}
- edit       Replace a unique string in a file. args: {"path": str, "old_string": str, "new_string": str}
- bash       Run a shell command. args: {"command": str}
- grep       Search for a pattern. args: {"pattern": str, "path": str}
- find       List files under a directory. args: {"directory": str}
- ls         List a directory. args: {"path": str}

Call tools one at a time. After a tool result, decide whether more tools are needed or
provide a final answer. Keep responses concise. When done, answer the user in plain text
with NO tool_call tags."""


def build_full_system_prompt(
    cwd: str = "",
    no_context_files: bool = False,
    system_override: str = "",
    append_system: str = "",
) -> str:
    """Assemble the full system prompt: preamble + tools + context + meta."""
    if not cwd:
        cwd = os.getcwd()
    ctx = compose_context(cwd, no_context_files=no_context_files)

    parts: list[str] = []
    if system_override:
        parts.append(system_override)
    elif ctx.get("system_override"):
        parts.append(str(ctx["system_override"]))
    else:
        parts.append(
            "You are mojopi, a local coding assistant powered by Modular MAX (or MLX on Apple Silicon).\n"
            "You help users understand, write, debug, and refactor code. You have access to tools for "
            "reading, writing, and running commands on the local filesystem. Be concise."
        )

    parts.append("## Tools\n\n" + TOOL_DESCRIPTIONS)

    context_files = ctx.get("context_files") or []
    if context_files:
        parts.append("## Context\n\n" + "\n\n---\n\n".join(context_files))

    if ctx.get("global_agents_md"):
        parts.append("## Global AGENTS.md\n\n" + str(ctx["global_agents_md"]))

    parts.append(f"## Session info\n\nDate: {date.today().isoformat()}\nWorking directory: {cwd}")

    project_append = ctx.get("append_system")
    if append_system:
        parts.append(append_system)
    elif project_append:
        parts.append(str(project_append))

    return "\n\n".join(parts)
