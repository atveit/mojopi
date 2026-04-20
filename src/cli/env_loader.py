"""Load .env files and export to os.environ.

Loads from two locations (first wins, so cwd takes priority):
  1. ./.env (current working dir)
  2. ~/.pi/.env (user-global)

Variables already set in os.environ are NOT overridden — shell exports win.

Supported keys (documented, not enforced):
  MOJOPI_MODEL              default model repo
  MOJOPI_MAX_NEW_TOKENS     int, token cap
  MOJOPI_AUTO_MEMORY        "0"/"1" — opt into auto memory injection
  MOJOPI_SESSION            default session id/prefix to resume
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional

# Recognized keys; used for documentation only.
KNOWN_KEYS = {
    "MOJOPI_MODEL",
    "MOJOPI_MAX_NEW_TOKENS",
    "MOJOPI_AUTO_MEMORY",
    "MOJOPI_SESSION",
    "MOJOPI_SYSTEM_PROMPT",
    "HF_HOME",
    "HF_TOKEN",
}


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file; ignore comments and empty lines.

    Tolerant: malformed lines are silently skipped.
    Simple format: KEY=VALUE, optional double or single quotes on value.
    No escape-sequence processing beyond stripping quotes.
    """
    result: dict[str, str] = {}
    if not path.exists():
        return result
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return result
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching outer quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        result[key] = value
    return result


def load_dotenv(
    cwd_env: Optional[Path] = None,
    user_env: Optional[Path] = None,
    override: bool = False,
) -> dict[str, str]:
    """Load .env files and export to os.environ.

    Args:
      cwd_env: override path to cwd .env (defaults to Path.cwd() / .env)
      user_env: override path to user .env (defaults to ~/.pi/.env)
      override: if True, overwrite existing os.environ values

    Returns the dict of values that were newly set (after applying override rules).
    """
    cwd_env = cwd_env if cwd_env is not None else Path.cwd() / ".env"
    user_env = user_env if user_env is not None else Path("~/.pi/.env").expanduser()

    # User .env first, then cwd overrides user.
    merged = {}
    merged.update(parse_env_file(user_env))
    merged.update(parse_env_file(cwd_env))

    newly_set: dict[str, str] = {}
    for k, v in merged.items():
        if override or k not in os.environ:
            os.environ[k] = v
            newly_set[k] = v
    return newly_set


def get_env_int(key: str, default: int = 0) -> int:
    """Safe integer env read; returns default on any failure."""
    raw = os.environ.get(key, "")
    try:
        return int(raw) if raw else default
    except (ValueError, TypeError):
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Safe bool env read; '0','false','no','off','' → False; anything else → True."""
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def show_active() -> str:
    """Return a summary of active MOJOPI_* env vars, for `mojopi --show-env`."""
    lines = ["Active mojopi environment:"]
    for k in sorted(KNOWN_KEYS):
        v = os.environ.get(k)
        if v is not None:
            # Mask tokens
            if "TOKEN" in k:
                shown = (v[:4] + "…") if v else "(empty)"
            else:
                shown = v
            lines.append(f"  {k}={shown}")
    if len(lines) == 1:
        lines.append("  (no MOJOPI_* vars set)")
    return "\n".join(lines)
