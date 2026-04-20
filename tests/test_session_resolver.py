"""Tests for agent/session_resolver.py — session ID resolution + listing."""
import sys, json, time
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolated(tmp_path):
    from agent.session_resolver import set_sessions_dir
    set_sessions_dir(str(tmp_path))
    yield


def _make_session(tmp_path, session_id: str, n_messages: int = 1) -> None:
    """Create a fake session directory with a transcript.jsonl."""
    d = tmp_path / session_id
    d.mkdir(parents=True, exist_ok=True)
    tp = d / "transcript.jsonl"
    with tp.open("w", encoding="utf-8") as f:
        for i in range(n_messages):
            f.write(json.dumps({"type": "message", "role": "user", "content": f"msg{i}"}) + "\n")


def test_module_importable():
    from agent import session_resolver
    assert hasattr(session_resolver, "resolve_session_id")
    assert hasattr(session_resolver, "list_all_sessions")
    assert hasattr(session_resolver, "get_latest_session_id")
    assert hasattr(session_resolver, "AmbiguousPrefixError")


def test_resolve_nonexistent_raises(tmp_path):
    from agent.session_resolver import resolve_session_id
    with pytest.raises(FileNotFoundError):
        resolve_session_id("never-exists")


def test_resolve_full_id(tmp_path):
    from agent.session_resolver import resolve_session_id
    _make_session(tmp_path, "a1b2c3d4-1111-2222-3333-deadbeefcafe")
    assert resolve_session_id("a1b2c3d4-1111-2222-3333-deadbeefcafe") == "a1b2c3d4-1111-2222-3333-deadbeefcafe"


def test_resolve_by_prefix(tmp_path):
    from agent.session_resolver import resolve_session_id
    _make_session(tmp_path, "abc12345-aaaa-bbbb-cccc-111122223333")
    _make_session(tmp_path, "xyz98765-ffff-eeee-dddd-888877776666")
    assert resolve_session_id("abc") == "abc12345-aaaa-bbbb-cccc-111122223333"
    assert resolve_session_id("xyz9") == "xyz98765-ffff-eeee-dddd-888877776666"


def test_resolve_ambiguous_prefix_raises(tmp_path):
    from agent.session_resolver import resolve_session_id, AmbiguousPrefixError
    _make_session(tmp_path, "abc1-xxx-xxx-xxx")
    _make_session(tmp_path, "abc2-yyy-yyy-yyy")
    with pytest.raises(AmbiguousPrefixError):
        resolve_session_id("abc")


def test_list_sessions_empty(tmp_path):
    from agent.session_resolver import list_all_sessions
    assert list_all_sessions() == []


def test_list_sessions_populated(tmp_path):
    from agent.session_resolver import list_all_sessions
    _make_session(tmp_path, "sess-1", n_messages=2)
    _make_session(tmp_path, "sess-2", n_messages=3)
    sessions = list_all_sessions()
    assert len(sessions) == 2
    ids = {s.session_id for s in sessions}
    assert ids == {"sess-1", "sess-2"}


def test_list_sessions_sorted_by_mtime(tmp_path):
    from agent.session_resolver import list_all_sessions
    _make_session(tmp_path, "older", 1)
    time.sleep(0.02)
    _make_session(tmp_path, "newer", 1)
    sessions = list_all_sessions()
    assert sessions[0].session_id == "newer"
    assert sessions[1].session_id == "older"


def test_list_sessions_message_counts(tmp_path):
    from agent.session_resolver import list_all_sessions
    _make_session(tmp_path, "sess-a", n_messages=5)
    sessions = list_all_sessions()
    assert sessions[0].message_count == 5


def test_get_latest_session_none_when_empty(tmp_path):
    from agent.session_resolver import get_latest_session_id
    assert get_latest_session_id() is None


def test_get_latest_session_id(tmp_path):
    from agent.session_resolver import get_latest_session_id
    _make_session(tmp_path, "old", 1)
    time.sleep(0.02)
    _make_session(tmp_path, "new", 1)
    assert get_latest_session_id() == "new"


def test_resolve_by_absolute_path(tmp_path):
    from agent.session_resolver import resolve_session_id
    _make_session(tmp_path, "by-path", 1)
    # Pass the transcript path directly — should extract session id from parent.
    transcript = tmp_path / "by-path" / "transcript.jsonl"
    assert resolve_session_id(str(transcript)) == "by-path"


def test_session_exists_at(tmp_path):
    from agent.session_resolver import session_exists_at
    _make_session(tmp_path, "real", 1)
    assert session_exists_at("real")
    assert not session_exists_at("fake")


def test_empty_session_id_raises(tmp_path):
    from agent.session_resolver import resolve_session_id
    with pytest.raises(FileNotFoundError):
        resolve_session_id("")
