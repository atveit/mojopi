"""Tests for agent/session_manager.py — session resume + per-turn persistence."""
import sys
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolated_sessions(tmp_path):
    from agent.session_manager import set_sessions_dir
    set_sessions_dir(str(tmp_path))
    yield


def test_module_importable():
    from agent import session_manager
    assert hasattr(session_manager, "new_session_id")
    assert hasattr(session_manager, "save_turn")
    assert hasattr(session_manager, "load_session_history")
    assert hasattr(session_manager, "HistoryDict")


def test_new_session_id_is_unique():
    from agent.session_manager import new_session_id
    ids = {new_session_id() for _ in range(20)}
    assert len(ids) == 20


def test_session_exists_false_by_default():
    from agent.session_manager import session_exists
    assert not session_exists("does-not-exist")


def test_save_then_load_round_trip():
    from agent.session_manager import save_turn, load_session_history, HistoryDict, new_session_id
    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="hello"))
    save_turn(sid, HistoryDict(role="assistant", content="hi"))
    history = load_session_history(sid)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].content == "hi"


def test_tool_result_round_trip():
    from agent.session_manager import save_turn, load_session_history, HistoryDict, new_session_id
    sid = new_session_id()
    save_turn(sid, HistoryDict(
        role="tool_result", content="file contents",
        tool_call_id="tc_0", tool_name="read"))
    history = load_session_history(sid)
    assert len(history) == 1
    assert history[0].tool_call_id == "tc_0"
    assert history[0].tool_name == "read"


def test_session_message_count():
    from agent.session_manager import save_turn, session_message_count, HistoryDict, new_session_id
    sid = new_session_id()
    assert session_message_count(sid) == 0
    save_turn(sid, HistoryDict(role="user", content="x"))
    save_turn(sid, HistoryDict(role="user", content="y"))
    assert session_message_count(sid) == 2


def test_load_missing_session_returns_empty():
    from agent.session_manager import load_session_history
    assert load_session_history("nonexistent-xyz") == []


def test_session_exists_after_save():
    from agent.session_manager import save_turn, session_exists, HistoryDict, new_session_id
    sid = new_session_id()
    assert not session_exists(sid)
    save_turn(sid, HistoryDict(role="user", content="x"))
    assert session_exists(sid)


def test_jsonl_format_is_parseable():
    """Transcript lines must be valid JSON (one per line) — future tooling compat."""
    from agent.session_manager import save_turn, HistoryDict, new_session_id, _transcript_path
    import json
    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="line1"))
    save_turn(sid, HistoryDict(role="assistant", content="line2"))
    lines = _transcript_path(sid).read_text().strip().split("\n")
    for line in lines:
        rec = json.loads(line)
        assert rec["type"] == "message"
        assert "timestamp" in rec


def test_two_sessions_dont_cross_talk():
    from agent.session_manager import save_turn, load_session_history, HistoryDict, new_session_id
    a = new_session_id()
    b = new_session_id()
    save_turn(a, HistoryDict(role="user", content="A1"))
    save_turn(b, HistoryDict(role="user", content="B1"))
    save_turn(a, HistoryDict(role="user", content="A2"))
    ha = load_session_history(a)
    hb = load_session_history(b)
    assert [h.content for h in ha] == ["A1", "A2"]
    assert [h.content for h in hb] == ["B1"]
