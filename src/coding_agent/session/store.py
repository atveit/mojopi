"""
store.py — Python JSONL reader/writer and session-tree utilities.

Ports the relevant logic from:
  pi-mono/packages/coding-agent/src/core/session-manager.ts  (schema v3)

All public functions operate on plain Python dicts; the Mojo side calls them
via Python interop (store.mojo).

Schema v3 entry types (7 total):
  session, message, thinking_level_change, model_change,
  compaction, branch_summary, custom, custom_message

Every entry has `id: str` and `parentId: str | None`.  The first entry
(type "session") always has parentId = None.  All other entries reference
their parent through parentId, forming a tree.
"""

from __future__ import annotations

import json
from typing import Optional


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def read_session(path: str) -> list[dict]:
    """Read a JSONL file and return a list of parsed entry dicts.

    Each non-empty line must be a valid JSON object.  Blank lines are skipped
    (tolerant of trailing newlines).

    Args:
        path: Absolute or relative filesystem path to a .jsonl file.

    Returns:
        Ordered list of dicts, one per non-blank line.

    Raises:
        FileNotFoundError: if *path* does not exist.
        json.JSONDecodeError: if any line is not valid JSON.
    """
    entries: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def write_session(path: str, entries: list[dict]) -> None:
    """Write *entries* as JSONL (one compact JSON object per line).

    The file is truncated/created at *path*.  Entries are written in the order
    they appear in the list.  No trailing newline is added after the last entry
    (each line ends with \\n, but the final \\n is the line terminator of the
    last entry, matching the JSONL spec).

    Args:
        path: Destination file path.  Parent directory must already exist.
        entries: List of dicts to serialise.
    """
    with open(path, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


# ---------------------------------------------------------------------------
# Tree utilities
# ---------------------------------------------------------------------------


def get_leaf_branches(entries: list[dict]) -> list[str]:
    """Return ids of all leaf entries (entries with no children).

    An entry is a *leaf* if no other entry lists it as its parentId.  In a
    linear session the single leaf is the last entry; in a branched session
    there are multiple leaves (one per branch tip).

    Args:
        entries: Full list of session entries as returned by read_session().

    Returns:
        List of id strings for leaf entries, in the order the entries appear
        in the source list.
    """
    parent_ids: set[str] = set()
    for entry in entries:
        pid = entry.get("parentId")
        if pid is not None:
            parent_ids.add(pid)

    return [e["id"] for e in entries if e["id"] not in parent_ids]


def resolve_path(entries: list[dict], leaf_id: str) -> list[dict]:
    """Walk from *leaf_id* up the parent chain to root.

    Returns an ordered list **root → leaf** (i.e. the path is reversed from
    the walk direction so callers receive a chronologically ordered sequence).

    Args:
        entries: Full list of session entries.
        leaf_id: The id of the entry to start the walk from.

    Returns:
        List of entry dicts from root to *leaf_id*, inclusive.

    Raises:
        KeyError: if *leaf_id* does not exist in *entries*.
        ValueError: if a parentId reference cannot be resolved (broken chain).
    """
    # Build an id → entry index for O(1) lookup.
    by_id: dict[str, dict] = {e["id"]: e for e in entries}

    if leaf_id not in by_id:
        raise KeyError(f"resolve_path: id {leaf_id!r} not found in entries")

    # Walk parent chain, collecting nodes.
    path: list[dict] = []
    current_id: Optional[str] = leaf_id
    visited: set[str] = set()

    while current_id is not None:
        if current_id in visited:
            raise ValueError(f"resolve_path: cycle detected at id {current_id!r}")
        if current_id not in by_id:
            raise ValueError(f"resolve_path: parentId {current_id!r} not found in entries")
        visited.add(current_id)
        node = by_id[current_id]
        path.append(node)
        current_id = node.get("parentId")  # None stops the loop

    # path is leaf→root; reverse to root→leaf.
    path.reverse()
    return path


def get_messages_from_path(entries: list[dict], leaf_id: str) -> list[dict]:
    """Return only MessageEntry items from the resolved path, in order.

    Calls resolve_path() and filters the result to entries with
    ``type == "message"``.

    Args:
        entries: Full list of session entries.
        leaf_id: The leaf id defining which branch to read.

    Returns:
        Ordered list (root → leaf) of entries whose type is "message".
    """
    path = resolve_path(entries, leaf_id)
    return [e for e in path if e.get("type") == "message"]
