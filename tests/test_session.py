"""
tests/test_session.py — pytest tests for coding_agent.session.store.

Run with:
    cd /Users/amund/mojopi/mojopi
    PYTHONPATH=src:${PYTHONPATH:-} python -m pytest tests/test_session.py -v

Coverage:
    1. read_session returns the correct number of entries from the fixture.
    2. All 7 entry types are present in the fixture.
    3. write_session + read_session round-trips losslessly.
    4. get_leaf_branches returns the correct leaf ids.
    5. resolve_path returns entries in root→leaf order.
    6. get_messages_from_path filters to only message entries.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from coding_agent.session.store import (
    get_leaf_branches,
    get_messages_from_path,
    read_session,
    resolve_path,
    write_session,
)

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_SESSION = FIXTURES_DIR / "sample_session.jsonl"

# ---------------------------------------------------------------------------
# Expected schema constants
# ---------------------------------------------------------------------------

ALL_ENTRY_TYPES = {
    "session",
    "message",
    "thinking_level_change",
    "model_change",
    "compaction",
    "branch_summary",
    "custom",
    "custom_message",
}

# The fixture has exactly 9 entries (1 header + 8 typed entries).
EXPECTED_ENTRY_COUNT = 9


# ---------------------------------------------------------------------------
# Test 1: read_session returns the correct number of entries
# ---------------------------------------------------------------------------


def test_read_session_entry_count():
    """read_session on the fixture file returns the expected number of entries."""
    entries = read_session(str(SAMPLE_SESSION))
    assert len(entries) == EXPECTED_ENTRY_COUNT, (
        f"Expected {EXPECTED_ENTRY_COUNT} entries, got {len(entries)}"
    )


# ---------------------------------------------------------------------------
# Test 2: all 7 entry types are present in the fixture
# ---------------------------------------------------------------------------


def test_all_entry_types_present():
    """All 7 v3 entry types appear in the fixture."""
    entries = read_session(str(SAMPLE_SESSION))
    found_types = {e["type"] for e in entries}
    missing = ALL_ENTRY_TYPES - found_types
    assert not missing, f"Missing entry types: {missing}"


# ---------------------------------------------------------------------------
# Test 3: write_session + read_session round-trip is lossless
# ---------------------------------------------------------------------------


def test_round_trip_lossless():
    """write_session followed by read_session yields identical entries."""
    original = read_session(str(SAMPLE_SESSION))

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as tmp:
        tmp_path = tmp.name

    try:
        write_session(tmp_path, original)
        reloaded = read_session(tmp_path)

        assert len(reloaded) == len(original), (
            f"Round-trip entry count mismatch: {len(reloaded)} vs {len(original)}"
        )

        for i, (orig, loaded) in enumerate(zip(original, reloaded)):
            assert orig == loaded, (
                f"Entry {i} changed after round-trip:\n"
                f"  original: {json.dumps(orig)}\n"
                f"  reloaded: {json.dumps(loaded)}"
            )
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test 4: get_leaf_branches returns correct leaf ids
# ---------------------------------------------------------------------------


def test_get_leaf_branches_linear_session():
    """In a purely linear session the single leaf is the last entry."""
    entries = read_session(str(SAMPLE_SESSION))
    leaves = get_leaf_branches(entries)

    # The fixture is a single linear chain; the last entry (cm1) is the leaf.
    assert leaves == ["cm1"], f"Expected ['cm1'], got {leaves}"


def test_get_leaf_branches_branched():
    """In a branched session both branch tips are returned as leaves."""
    # Construct a minimal branched session in-memory:
    #   root → a → b   (leaf: b)
    #       └─→ c      (leaf: c)
    entries = [
        {"type": "session", "v": 3, "id": "root", "parentId": None, "cwd": "/", "timestamp": 1},
        {"type": "message", "id": "a", "parentId": "root", "message": {"role": "user", "content": []}},
        {"type": "message", "id": "b", "parentId": "a", "message": {"role": "assistant", "content": []}},
        {"type": "message", "id": "c", "parentId": "root", "message": {"role": "user", "content": []}},
    ]
    leaves = get_leaf_branches(entries)
    assert set(leaves) == {"b", "c"}, f"Expected {{b, c}}, got {set(leaves)}"


# ---------------------------------------------------------------------------
# Test 5: resolve_path returns entries in root→leaf order
# ---------------------------------------------------------------------------


def test_resolve_path_order():
    """resolve_path(entries, 'cm1') returns the full chain root→cm1."""
    entries = read_session(str(SAMPLE_SESSION))
    path = resolve_path(entries, "cm1")

    # Expected id sequence (all 9 entries, root first):
    expected_ids = ["root", "m1", "m2", "t1", "mc1", "c1", "bs1", "ce1", "cm1"]
    actual_ids = [e["id"] for e in path]

    assert actual_ids == expected_ids, (
        f"Path id order mismatch.\n  expected: {expected_ids}\n  actual:   {actual_ids}"
    )


def test_resolve_path_partial():
    """resolve_path with a mid-chain id returns only the partial chain."""
    entries = read_session(str(SAMPLE_SESSION))
    path = resolve_path(entries, "m2")
    actual_ids = [e["id"] for e in path]
    assert actual_ids == ["root", "m1", "m2"], (
        f"Partial path mismatch: {actual_ids}"
    )


def test_resolve_path_unknown_id_raises():
    """resolve_path raises KeyError for an unknown leaf_id."""
    entries = read_session(str(SAMPLE_SESSION))
    with pytest.raises(KeyError):
        resolve_path(entries, "does-not-exist")


# ---------------------------------------------------------------------------
# Test 6: get_messages_from_path filters to only message entries
# ---------------------------------------------------------------------------


def test_get_messages_from_path_only_messages():
    """get_messages_from_path returns only type='message' entries."""
    entries = read_session(str(SAMPLE_SESSION))
    messages = get_messages_from_path(entries, "cm1")

    assert all(m["type"] == "message" for m in messages), (
        "Non-message entry leaked through: "
        + str([m for m in messages if m["type"] != "message"])
    )


def test_get_messages_from_path_count():
    """get_messages_from_path on the full fixture returns exactly 2 messages."""
    entries = read_session(str(SAMPLE_SESSION))
    messages = get_messages_from_path(entries, "cm1")
    # Fixture has m1 (user) and m2 (assistant) — 2 message entries total.
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"


def test_get_messages_from_path_roles():
    """Messages from the full fixture are user then assistant."""
    entries = read_session(str(SAMPLE_SESSION))
    messages = get_messages_from_path(entries, "cm1")
    roles = [m["message"]["role"] for m in messages]
    assert roles == ["user", "assistant"], f"Unexpected role order: {roles}"
