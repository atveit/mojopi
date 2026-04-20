"""Interactive REPL helpers — called from Mojo main.mojo.

Two concerns live here rather than in Mojo because they're much cleaner in
Python:

1. Rich markdown rendering of agent responses (so code blocks, lists, bold
   render the way users expect from Claude Code / Codex-style tools).
2. Environment-variable defaults for common CliArgs (so users can set
   MOJOPI_MODEL once and forget it).
"""
from __future__ import annotations
import os
from pathlib import Path

_rich_ok = False
try:
    from rich.console import Console
    from rich.markdown import Markdown
    _console = Console()
    _rich_ok = True
except ImportError:
    _console = None


def render_response(text: str) -> None:
    """Pretty-print an agent response.

    Uses Rich Markdown rendering when available; falls back to plain stdout
    so the tool still works in minimal environments (e.g. CI without Rich).
    """
    if _rich_ok and _console is not None:
        try:
            _console.print(Markdown(text))
            return
        except Exception:
            pass
    print(text)


def env_model_default() -> str:
    """Return MOJOPI_MODEL or empty string."""
    return os.environ.get("MOJOPI_MODEL", "")


def env_max_new_tokens_default() -> int:
    """Return MOJOPI_MAX_NEW_TOKENS as int, or 0 if unset/invalid."""
    raw = os.environ.get("MOJOPI_MAX_NEW_TOKENS", "")
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def read_file_for_slash_command(path: str) -> str:
    """Read a file for the `/file <path>` slash command.

    Tildes are expanded. Returns the file contents as a string; raises
    FileNotFoundError if the path doesn't exist.
    """
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"file not found: {path}")
    return p.read_text(encoding="utf-8")


def welcome_banner(version: str) -> str:
    """Return a short welcome banner for the REPL."""
    hint = "Type /help for commands, /exit to quit."
    return f"mojopi {version} — interactive mode. {hint}"
