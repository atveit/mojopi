"""Full-text search across mojopi session transcripts.

Usage (programmatic):
    from cli.search import search_sessions
    results = search_sessions("auth token", max_results=20)

Usage (CLI — via main.mojo subcommand, wired by lead):
    mojopi search "auth token"

No index, no dependency — plain JSONL parse + substring match on content.
"""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SESSIONS_DIR = Path("~/.pi/sessions").expanduser()


@dataclass
class SearchHit:
    session_id: str
    turn_index: int
    role: str
    snippet: str
    timestamp: str = ""
    mtime: float = 0.0

    def format(self) -> str:
        return (
            f"  {self.session_id[:8]} turn {self.turn_index:>3} [{self.role}] "
            f"{self.timestamp[:19] if self.timestamp else '':<20} {self.snippet}"
        )


def _snippet_around_match(content: str, pattern: str, context: int = 60) -> str:
    """Return ~context chars around the first case-insensitive match."""
    idx = content.lower().find(pattern.lower())
    if idx < 0:
        return content[:context].replace("\n", " ")
    start = max(0, idx - context // 2)
    end = min(len(content), idx + len(pattern) + context // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return (prefix + content[start:end].replace("\n", " ") + suffix)


def _iter_session_dirs() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return [
        d for d in SESSIONS_DIR.iterdir()
        if d.is_dir() and (d / "transcript.jsonl").exists()
    ]


def search_sessions(
    query: str,
    max_results: int = 50,
    case_insensitive: bool = True,
    role_filter: Optional[str] = None,
) -> list[SearchHit]:
    """Search all sessions for messages matching `query`.

    Args:
      query: substring to find
      max_results: cap returned hits (newest sessions first)
      case_insensitive: default True
      role_filter: restrict to "user" / "assistant" / "tool_result" if set

    Returns list sorted by session mtime DESC, then turn_index.
    """
    if not query:
        return []

    pattern = query.lower() if case_insensitive else query
    hits: list[SearchHit] = []

    dirs = _iter_session_dirs()
    # Sort by mtime DESC so newest sessions' hits come first.
    dirs.sort(key=lambda d: (d / "transcript.jsonl").stat().st_mtime, reverse=True)

    for sess_dir in dirs:
        tp = sess_dir / "transcript.jsonl"
        mtime = tp.stat().st_mtime
        try:
            turn_index = 0
            with tp.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("type") != "message":
                        continue
                    turn_index += 1
                    if role_filter and rec.get("role") != role_filter:
                        continue
                    content = rec.get("content", "")
                    haystack = content.lower() if case_insensitive else content
                    if pattern in haystack:
                        hits.append(SearchHit(
                            session_id=sess_dir.name,
                            turn_index=turn_index,
                            role=rec.get("role", ""),
                            snippet=_snippet_around_match(content, query),
                            timestamp=rec.get("timestamp", ""),
                            mtime=mtime,
                        ))
                        if len(hits) >= max_results:
                            return hits
        except OSError:
            continue

    return hits


def format_results(hits: list[SearchHit], query: str) -> str:
    """Human-readable multi-line formatter for hits."""
    if not hits:
        return f"no matches for {query!r}"
    lines = [f"{len(hits)} hit(s) for {query!r}:"]
    for h in hits:
        lines.append(h.format())
    return "\n".join(lines)


def set_sessions_dir(path: str) -> None:
    """Override the sessions dir (tests only)."""
    global SESSIONS_DIR
    SESSIONS_DIR = Path(path).expanduser()
