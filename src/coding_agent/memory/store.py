"""Memory store: append-only JSONL at ~/.pi/memory/memory.jsonl + in-RAM cache."""
from __future__ import annotations
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path("~/.pi/memory").expanduser()
MEMORY_FILE = MEMORY_DIR / "memory.jsonl"

# Entry types
TYPE_USER_PREFERENCE = "user_preference"
TYPE_PROJECT_FACT = "project_fact"
TYPE_TOOL_OBSERVATION = "tool_observation"
TYPE_DECISION = "decision"
VALID_TYPES = {TYPE_USER_PREFERENCE, TYPE_PROJECT_FACT, TYPE_TOOL_OBSERVATION, TYPE_DECISION}


@dataclass
class MemoryEntry:
    id: str
    text: str
    embedding: list[float]
    timestamp: str
    source: str
    type: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "MemoryEntry":
        return MemoryEntry(
            id=d["id"], text=d["text"], embedding=d.get("embedding", []),
            timestamp=d["timestamp"], source=d.get("source", ""),
            type=d.get("type", TYPE_PROJECT_FACT),
            confidence=float(d.get("confidence", 1.0)),
        )


_cache: list[MemoryEntry] = []
_cache_loaded = False


def _new_id() -> str:
    return f"mem_{int(time.time())}_{uuid.uuid4().hex[:6]}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_cache() -> None:
    global _cache_loaded
    _cache.clear()
    if MEMORY_FILE.exists():
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    _cache.append(MemoryEntry.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError):
                    continue
    _cache_loaded = True


def _ensure_loaded() -> None:
    if not _cache_loaded:
        _load_cache()


def store_memory(
    text: str,
    embedding: list[float],
    source: str = "",
    type: str = TYPE_PROJECT_FACT,
    confidence: float = 1.0,
) -> MemoryEntry:
    """Append a new memory entry. Returns the created entry."""
    _ensure_dir()
    _ensure_loaded()
    if type not in VALID_TYPES:
        type = TYPE_PROJECT_FACT
    entry = MemoryEntry(
        id=_new_id(), text=text, embedding=list(embedding),
        timestamp=_now_iso(), source=source, type=type, confidence=confidence,
    )
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")
    _cache.append(entry)
    return entry


def list_memories(type: Optional[str] = None) -> list[MemoryEntry]:
    _ensure_loaded()
    if type is None:
        return list(_cache)
    return [e for e in _cache if e.type == type]


def forget_memory(entry_id: str) -> bool:
    """Remove an entry by id. Rewrites the JSONL file. Returns True if found."""
    _ensure_loaded()
    before = len(_cache)
    _cache[:] = [e for e in _cache if e.id != entry_id]
    if len(_cache) == before:
        return False
    _ensure_dir()
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        for e in _cache:
            f.write(json.dumps(e.to_dict()) + "\n")
    return True


def clear_all_memories() -> int:
    """Clear the store (used by tests). Returns count cleared."""
    _ensure_loaded()
    n = len(_cache)
    _cache.clear()
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()
    return n


def set_memory_dir(path: str) -> None:
    """Override memory directory (tests only)."""
    global MEMORY_DIR, MEMORY_FILE, _cache_loaded
    MEMORY_DIR = Path(path).expanduser()
    MEMORY_FILE = MEMORY_DIR / "memory.jsonl"
    _cache_loaded = False
    _cache.clear()
