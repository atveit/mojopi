"""Session ID resolution + listing.

Resolves UUID prefixes to full session IDs, lists sessions, finds the
latest. The session directory layout matches agent.session_manager:

  ~/.pi/sessions/<uuid>/transcript.jsonl
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SESSIONS_DIR = Path("~/.pi/sessions").expanduser()


@dataclass
class SessionInfo:
    session_id: str
    path: Path
    mtime: float
    message_count: int

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "path": str(self.path),
            "mtime": self.mtime,
            "message_count": self.message_count,
        }


class AmbiguousPrefixError(ValueError):
    """Raised when a prefix matches multiple session IDs."""
    def __init__(self, prefix: str, matches: list[str]):
        super().__init__(
            f"session prefix {prefix!r} is ambiguous — matches {len(matches)}: "
            + ", ".join(sorted(matches)[:5])
            + ("..." if len(matches) > 5 else "")
        )
        self.prefix = prefix
        self.matches = matches


def set_sessions_dir(path: str) -> None:
    """Override sessions directory (tests only)."""
    global SESSIONS_DIR
    SESSIONS_DIR = Path(path).expanduser()


def _session_dirs() -> list[Path]:
    """Return all <session_id> directories that have a transcript.jsonl."""
    if not SESSIONS_DIR.exists():
        return []
    dirs = []
    for child in SESSIONS_DIR.iterdir():
        if child.is_dir() and (child / "transcript.jsonl").exists():
            dirs.append(child)
    return dirs


def _count_messages(transcript_path: Path) -> int:
    n = 0
    if not transcript_path.exists():
        return 0
    with transcript_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("type") == "message":
                    n += 1
            except json.JSONDecodeError:
                continue
    return n


def list_all_sessions() -> list[SessionInfo]:
    """Return all sessions, sorted by mtime DESC (newest first)."""
    results = []
    for d in _session_dirs():
        tp = d / "transcript.jsonl"
        results.append(SessionInfo(
            session_id=d.name,
            path=tp,
            mtime=tp.stat().st_mtime,
            message_count=_count_messages(tp),
        ))
    results.sort(key=lambda s: s.mtime, reverse=True)
    return results


def resolve_session_id(id_or_prefix: str) -> str:
    """Resolve a prefix (or full ID, or path) to the full session ID.

    Raises:
        FileNotFoundError — no match
        AmbiguousPrefixError — multiple matches
    """
    if not id_or_prefix:
        raise FileNotFoundError("empty session id")

    # If it's an absolute path to a transcript file, extract parent dir name.
    p = Path(id_or_prefix)
    if p.exists() and p.is_file():
        return p.parent.name
    if p.exists() and p.is_dir():
        return p.name

    all_sessions = _session_dirs()
    exact = [s.name for s in all_sessions if s.name == id_or_prefix]
    if exact:
        return exact[0]

    # Prefix match
    matches = [s.name for s in all_sessions if s.name.startswith(id_or_prefix)]
    if len(matches) == 0:
        raise FileNotFoundError(f"no session matches prefix {id_or_prefix!r}")
    if len(matches) > 1:
        raise AmbiguousPrefixError(id_or_prefix, matches)
    return matches[0]


def get_latest_session_id() -> Optional[str]:
    """Return the most recently modified session id, or None if no sessions exist."""
    sessions = list_all_sessions()
    if not sessions:
        return None
    return sessions[0].session_id


def session_exists_at(session_id: str) -> bool:
    """Check whether a full session id has a transcript on disk."""
    return (SESSIONS_DIR / session_id / "transcript.jsonl").exists()
