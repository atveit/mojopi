import sys
from pathlib import Path


def expand_at_file(prompt: str) -> str:
    """If prompt starts with '@', read contents from that file path."""
    if not prompt.startswith("@"):
        return prompt
    path = Path(prompt[1:]).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"@file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_stdin_prompt() -> str | None:
    """Read prompt from stdin if not a tty. Returns None if stdin is a tty."""
    if sys.stdin.isatty():
        return None
    try:
        return sys.stdin.read()
    except OSError:
        return None


def resolve_prompt(raw: str) -> str:
    """Resolve final prompt: @file expansion, then strip."""
    return expand_at_file(raw).strip()
