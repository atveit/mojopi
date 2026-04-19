"""Context loader — port of pi-mono resource-loader.ts:58-75.

Walks cwd→root collecting AGENTS.md / CLAUDE.md files, loads project-level
overrides from .pi/SYSTEM.md and .pi/APPEND_SYSTEM.md, and loads the global
~/.pi/agent/AGENTS.md.  The compose_context() function combines all sources
into a single dict consumed by the Mojo system-prompt builder.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_CONTEXT_FILENAMES = ("AGENTS.md", "CLAUDE.md")


def find_context_files(cwd: str, max_depth: int = 20) -> list[str]:
    """Walk from cwd up to root, collecting AGENTS.md and CLAUDE.md files.

    Returns paths in order from root → cwd (outermost first).
    Stops at filesystem root or after max_depth steps.
    """
    collected: list[str] = []
    current = Path(cwd).resolve()
    depth = 0

    while depth < max_depth:
        for name in _CONTEXT_FILENAMES:
            candidate = current / name
            if candidate.is_file():
                collected.append(str(candidate))
        parent = current.parent
        if parent == current:
            # Reached filesystem root.
            break
        current = parent
        depth += 1

    # collected is cwd-first; reverse to get root-first ordering.
    collected.reverse()
    return collected


def load_project_overrides(cwd: str) -> dict[str, Optional[str]]:
    """Load .pi/SYSTEM.md and .pi/APPEND_SYSTEM.md from cwd.

    Returns dict with keys 'system' and 'append_system', values are file
    contents or None when the file does not exist.
    """
    pi_dir = Path(cwd) / ".pi"
    system_path = pi_dir / "SYSTEM.md"
    append_path = pi_dir / "APPEND_SYSTEM.md"

    system: Optional[str] = None
    append_system: Optional[str] = None

    if system_path.is_file():
        system = system_path.read_text(encoding="utf-8")

    if append_path.is_file():
        append_system = append_path.read_text(encoding="utf-8")

    return {"system": system, "append_system": append_system}


def load_global_agents_md() -> Optional[str]:
    """Load ~/.pi/agent/AGENTS.md if it exists.

    Returns file contents or None.
    """
    global_path = Path.home() / ".pi" / "agent" / "AGENTS.md"
    if global_path.is_file():
        return global_path.read_text(encoding="utf-8")
    return None


def compose_context(
    cwd: str, no_context_files: bool = False
) -> dict[str, object]:
    """Combine all context sources.

    Returns:
        {
          'context_files': list[str]  — file contents, root-first order,
          'system_override': str | None,
          'append_system': str | None,
          'global_agents_md': str | None,
        }
    """
    context_files: list[str] = []

    if not no_context_files:
        paths = find_context_files(cwd)
        for p in paths:
            try:
                context_files.append(Path(p).read_text(encoding="utf-8"))
            except OSError:
                # Skip unreadable files rather than crashing.
                pass

    overrides = load_project_overrides(cwd)
    global_agents_md = load_global_agents_md()

    return {
        "context_files": context_files,
        "system_override": overrides["system"],
        "append_system": overrides["append_system"],
        "global_agents_md": global_agents_md,
    }
