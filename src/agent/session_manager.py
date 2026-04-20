"""Session resume + per-turn persistence for the agent loop.

Layers on top of coding_agent.session.store (the W1 v3 JSONL reader/writer).
Provides a HistoryEntry-shaped view that loop.mojo can replay from.

Default sessions directory: ~/.pi/sessions/
Each session lives in ~/.pi/sessions/<uuid>/transcript.jsonl
"""
from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SESSIONS_DIR = Path("~/.pi/sessions").expanduser()


@dataclass
class HistoryDict:
    """Plain-Python equivalent of the Mojo HistoryEntry struct."""
    role: str
    content: str
    tool_call_id: str = ""
    tool_name: str = ""

    def to_json(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
        }


def new_session_id() -> str:
    """Generate a fresh UUID4 session id."""
    return str(uuid.uuid4())


def _session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def _transcript_path(session_id: str) -> Path:
    return _session_dir(session_id) / "transcript.jsonl"


def session_exists(session_id: str) -> bool:
    return _transcript_path(session_id).exists()


def save_turn(session_id: str, entry: HistoryDict) -> None:
    """Append a single HistoryEntry to the session transcript."""
    d = _session_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)
    path = _transcript_path(session_id)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "type": "message",
        "timestamp": ts,
        **entry.to_json(),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_session_history(session_id: str) -> list[HistoryDict]:
    """Load message history for a session. Returns empty list if session missing."""
    path = _transcript_path(session_id)
    if not path.exists():
        return []
    entries: list[HistoryDict] = []
    with path.open("r", encoding="utf-8") as f:
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
            entries.append(HistoryDict(
                role=rec.get("role", ""),
                content=rec.get("content", ""),
                tool_call_id=rec.get("tool_call_id", ""),
                tool_name=rec.get("tool_name", ""),
            ))
    return entries


def session_message_count(session_id: str) -> int:
    return len(load_session_history(session_id))


def set_sessions_dir(path: str) -> None:
    """Override sessions directory (tests only)."""
    global SESSIONS_DIR
    SESSIONS_DIR = Path(path).expanduser()
