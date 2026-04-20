"""Tests for agent/compaction_bridge.py — auto-compaction triggering policy."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _make_entry(role: str, content: str) -> dict:
    return {"role": role, "content": content, "tool_call_id": "", "tool_name": ""}


def test_module_importable():
    from agent import compaction_bridge

    assert hasattr(compaction_bridge, "auto_compact_if_needed")
    assert hasattr(compaction_bridge, "should_auto_compact")
    assert hasattr(compaction_bridge, "estimate_history_tokens")


def test_empty_history_not_compacted():
    from agent.compaction_bridge import auto_compact_if_needed, should_auto_compact

    assert not should_auto_compact([])
    h, flag = auto_compact_if_needed([])
    assert h == []
    assert flag is False


def test_small_history_not_compacted():
    from agent.compaction_bridge import auto_compact_if_needed

    history = [_make_entry("user", "hi"), _make_entry("assistant", "hello")]
    h, flag = auto_compact_if_needed(history, max_tokens=8192)
    assert flag is False
    assert h == history


def test_large_history_triggers_compaction():
    from agent.compaction_bridge import should_auto_compact

    # Make enough tokens to cross 50% of a small budget.
    # Each entry has content length 2000 -> ~500 tokens (2000 // 4).
    # 20 entries * 500 = 10_000 tokens >> 0.5 * 2048 = 1024.
    big_content = "x" * 2000
    history = [_make_entry("user", big_content) for _ in range(20)]
    assert should_auto_compact(history, max_tokens=2048, threshold=0.5)


def test_estimate_history_tokens_sums():
    from agent.compaction_bridge import estimate_history_tokens

    # count_tokens = len // 4
    history = [_make_entry("user", "x" * 40), _make_entry("user", "y" * 80)]
    # 40/4 + 80/4 = 10 + 20 = 30
    assert estimate_history_tokens(history) == 30


def test_compaction_failure_returns_original(monkeypatch):
    """If _compact_history raises, return original history and flag=False."""
    from agent import compaction_bridge

    def raise_it(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(compaction_bridge, "_compact_history", raise_it)
    big = [_make_entry("user", "x" * 40_000)]
    h, flag = compaction_bridge.auto_compact_if_needed(big, max_tokens=1024)
    assert h == big  # unchanged
    assert flag is False


def test_threshold_respected():
    from agent.compaction_bridge import should_auto_compact

    history = [_make_entry("user", "x" * 4000)]  # ~1000 tokens
    assert should_auto_compact(history, max_tokens=2000, threshold=0.5)
    assert not should_auto_compact(history, max_tokens=4000, threshold=0.5)


def test_auto_compact_returns_shorter_history_when_triggered():
    """End-to-end: when the threshold is crossed, the returned history should
    be the compacted form (shorter or same length with a synthetic summary
    entry at the head) and the was_compacted flag should be True."""
    from agent.compaction_bridge import auto_compact_if_needed

    # 20 large entries push us well past any reasonable threshold.
    history = [_make_entry("user", "x" * 4000) for _ in range(20)]
    compacted, flag = auto_compact_if_needed(
        history, max_tokens=2048, threshold=0.5, keep_last_n=4
    )
    assert flag is True
    # Compacted form keeps last N plus a synthetic summary entry.
    assert len(compacted) < len(history)
    # The head entry should be the synthetic summary.
    assert compacted[0].get("role") == "system"
