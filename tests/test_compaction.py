import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import tempfile
from coding_agent.compaction.compactor import (
    estimate_tokens,
    estimate_history_tokens,
    should_compact,
    compact_history,
    write_compaction_entry,
)


def test_estimate_tokens_basic():
    assert estimate_tokens("hello") == 1   # 5 // 4 = 1
    assert estimate_tokens("a" * 400) == 100


def test_estimate_history_tokens():
    history = [
        {"role": "user", "content": "a" * 400},
        {"role": "assistant", "content": "b" * 400},
    ]
    # Each entry: role (~4 tokens) + content (100 tokens) = ~104 per entry = ~208 total
    total = estimate_history_tokens(history)
    assert total > 100


def test_should_compact_false_empty():
    assert not should_compact([], max_tokens=8192)


def test_should_compact_true_large():
    # 8192 * 0.75 = 6144 tokens threshold. Create history exceeding it.
    big = "x" * (6200 * 4)  # ~6200 tokens
    history = [{"role": "user", "content": big}]
    assert should_compact(history, max_tokens=8192)


def test_compact_history_keeps_last_n():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    new_hist, summary = compact_history(history, keep_last_n=4)
    # new_hist = [summary_entry] + last_4 = 5 entries
    assert len(new_hist) == 5
    assert new_hist[0]["role"] == "system"
    assert "Compacted" in new_hist[0]["content"]


def test_compact_history_short_passthrough():
    history = [{"role": "user", "content": "hi"}]
    new_hist, summary = compact_history(history, keep_last_n=4)
    assert new_hist == history
    assert summary == ""


def test_write_compaction_entry(tmp_path):
    from coding_agent.session.store import write_session, read_session
    session_file = str(tmp_path / "test.jsonl")
    # Start with a minimal session
    write_session(session_file, [
        {"type": "session", "v": 3, "id": "sess-1", "parentId": None, "cwd": "/tmp", "timestamp": 0},
    ])
    entry = write_compaction_entry(session_file, "sess-1", "Summary text.", 512)
    assert entry["type"] == "compaction"
    assert entry["summary"] == "Summary text."
    # Verify it was written
    entries = read_session(session_file)
    assert len(entries) == 2
    assert entries[1]["type"] == "compaction"
