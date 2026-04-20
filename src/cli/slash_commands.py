"""REPL slash-command dispatcher.

Each slash command returns a SlashResult with:
  - handled: bool       — was this input recognized as a slash command
  - output: str          — text to print to the user
  - new_session_id: Optional[str]  — set when /fork creates a new session
  - new_model: Optional[str]       — set when /model switches models
  - should_exit: bool    — for /exit and /quit (legacy pass-through)
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SlashResult:
    handled: bool = False
    output: str = ""
    new_session_id: Optional[str] = None
    new_model: Optional[str] = None
    should_exit: bool = False


@dataclass
class SlashState:
    session_id: str
    model: str
    system_prompt: str = ""


def dispatch_slash(line: str, state: SlashState) -> SlashResult:
    """Dispatch a slash command. Non-slash input returns handled=False."""
    line = line.strip()
    if not line.startswith("/"):
        return SlashResult(handled=False)

    parts = line.split(maxsplit=1)
    cmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    handlers = {
        "/exit": _h_exit, "/quit": _h_exit,
        "/model": _h_model,
        "/history": _h_history,
        "/save": _h_save,
        "/fork": _h_fork,
        "/tokens": _h_tokens,
        "/memory": _h_memory,
    }
    handler = handlers.get(cmd)
    if handler is None:
        return SlashResult(handled=True, output=f"unknown command: {cmd}")
    return handler(rest, state)


def _h_exit(_rest: str, _state: SlashState) -> SlashResult:
    return SlashResult(handled=True, should_exit=True)


def _h_model(rest: str, state: SlashState) -> SlashResult:
    repo = rest.strip()
    if not repo:
        return SlashResult(handled=True, output=f"current model: {state.model}")
    # Clear the pipeline caches so the new model is actually loaded
    try:
        import max_brain.pipeline as pm
        pm._pipeline_cache.clear()
    except Exception:
        pass
    try:
        import max_brain.mlx_backend as mx_mod
        mx_mod._mlx_cache.clear()
    except Exception:
        pass
    return SlashResult(handled=True, output=f"switched to {repo}", new_model=repo)


def _h_history(rest: str, state: SlashState) -> SlashResult:
    from agent.session_manager import load_session_history
    try:
        limit = int(rest.strip()) if rest.strip() else 10
    except ValueError:
        limit = 10
    history = load_session_history(state.session_id)
    if not history:
        return SlashResult(handled=True, output="(no history in this session)")
    shown = history[-limit:]
    lines = [f"-- {len(history)} turns total; showing last {len(shown)} --"]
    for i, h in enumerate(shown, start=len(history) - len(shown) + 1):
        snippet = h.content[:160].replace("\n", " ")
        if len(h.content) > 160:
            snippet += "..."
        lines.append(f"  {i}. [{h.role}] {snippet}")
    return SlashResult(handled=True, output="\n".join(lines))


def _h_save(rest: str, state: SlashState) -> SlashResult:
    from agent.session_manager import load_session_history
    path = rest.strip()
    if not path:
        return SlashResult(handled=True, output="usage: /save <path>")
    history = load_session_history(state.session_id)
    if not history:
        return SlashResult(handled=True, output="(nothing to save; session has no history)")
    md_lines = [f"# mojopi session {state.session_id[:8]}", ""]
    md_lines.append(f"Model: {state.model}")
    md_lines.append("")
    for h in history:
        role_header = "### You" if h.role == "user" else (
            "### Tool result" if h.role == "tool_result" else "### Assistant")
        md_lines.append(role_header)
        md_lines.append("")
        md_lines.append(h.content)
        md_lines.append("")
    try:
        Path(path).expanduser().write_text("\n".join(md_lines), encoding="utf-8")
    except OSError as e:
        return SlashResult(handled=True, output=f"save failed: {e}")
    return SlashResult(handled=True, output=f"saved {len(history)} turns to {path}")


def _h_fork(_rest: str, state: SlashState) -> SlashResult:
    from agent.session_manager import (
        load_session_history, new_session_id, save_turn, HistoryDict,
    )
    new_id = new_session_id()
    history = load_session_history(state.session_id)
    for h in history:
        save_turn(new_id, HistoryDict(
            role=h.role, content=h.content,
            tool_call_id=h.tool_call_id, tool_name=h.tool_name,
        ))
    return SlashResult(
        handled=True,
        output=f"forked session {state.session_id[:8]} \u2192 {new_id[:8]} ({len(history)} turns copied)",
        new_session_id=new_id,
    )


def _h_tokens(_rest: str, state: SlashState) -> SlashResult:
    from agent.session_manager import load_session_history
    history = load_session_history(state.session_id)
    try:
        from coding_agent.compaction.compactor import estimate_tokens
        count_fn = lambda s: estimate_tokens(s)
    except ImportError:
        count_fn = lambda s: len(s) // 4
    total = sum(count_fn(h.content) for h in history)
    total += count_fn(state.system_prompt)
    return SlashResult(
        handled=True,
        output=f"estimated {total} tokens across {len(history)} turns + system prompt",
    )


def _h_memory(rest: str, state: SlashState) -> SlashResult:
    from coding_agent.memory.store import list_memories, store_memory, forget_memory
    from coding_agent.memory.embeddings import embed_text

    parts = rest.split(maxsplit=1)
    sub = parts[0] if parts else "list"
    arg = parts[1] if len(parts) > 1 else ""

    if sub == "list" or sub == "":
        mems = list_memories()
        if not mems:
            return SlashResult(handled=True, output="(no memories stored)")
        lines = [f"-- {len(mems)} memories --"]
        for m in mems[-10:]:
            snippet = m.text[:80]
            lines.append(f"  {m.id[-8:]}  [{m.type}]  {snippet}")
        return SlashResult(handled=True, output="\n".join(lines))

    if sub == "add":
        text = arg.strip().strip('"').strip("'")
        if not text:
            return SlashResult(handled=True, output='usage: /memory add "<text>"')
        entry = store_memory(
            text=text,
            embedding=embed_text(text),
            source="user_added",
            type="user_preference",
            confidence=1.0,
        )
        return SlashResult(handled=True, output=f"added memory {entry.id[-8:]}")

    if sub == "forget":
        mem_id_or_suffix = arg.strip()
        if not mem_id_or_suffix:
            return SlashResult(handled=True, output="usage: /memory forget <id>")
        mems = list_memories()
        target = None
        for m in mems:
            if m.id == mem_id_or_suffix or m.id.endswith(mem_id_or_suffix):
                target = m
                break
        if target is None:
            return SlashResult(handled=True, output=f"no memory matching {mem_id_or_suffix!r}")
        forget_memory(target.id)
        return SlashResult(handled=True, output=f"forgot {target.id[-8:]}")

    return SlashResult(handled=True, output=f"unknown /memory subcommand: {sub}")


def help_text() -> str:
    return """Slash commands:
  /exit, /quit              exit the REPL
  /model <repo>             switch model (clears inference caches)
  /history [N]              show last N turns (default 10)
  /save <path>              export session as markdown
  /fork                     branch session (copy + new id)
  /tokens                   estimated prompt token count
  /memory list              list stored memories
  /memory add "<text>"      add a manual memory
  /memory forget <id>       remove memory by id
"""
