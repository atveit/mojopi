"""Tests for cli/search.py — session transcript search."""
import sys
import json
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path):
    from cli.search import set_sessions_dir
    set_sessions_dir(str(tmp_path))
    yield


def _make_session(sessions_dir, session_id: str, messages: list[tuple[str, str]]):
    """messages = [(role, content), ...]"""
    d = sessions_dir / session_id
    d.mkdir(parents=True, exist_ok=True)
    tp = d / "transcript.jsonl"
    with tp.open("w", encoding="utf-8") as f:
        for i, (role, content) in enumerate(messages):
            f.write(json.dumps({
                "type": "message",
                "role": role,
                "content": content,
                "timestamp": f"2026-04-20T12:{i:02d}:00Z",
            }) + "\n")


def test_module_importable():
    from cli import search
    assert hasattr(search, "search_sessions")
    assert hasattr(search, "SearchHit")
    assert hasattr(search, "format_results")


def test_empty_query_returns_no_hits(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [("user", "hello world")])
    assert search_sessions("") == []


def test_no_sessions(tmp_path):
    from cli.search import search_sessions
    assert search_sessions("anything") == []


def test_finds_user_message(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [
        ("user", "please find the auth token"),
        ("assistant", "I found it in config.py"),
    ])
    hits = search_sessions("auth token")
    assert len(hits) == 1
    assert hits[0].role == "user"
    assert "auth token" in hits[0].snippet.lower()


def test_finds_across_multiple_sessions(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [("user", "foo bar baz")])
    _make_session(tmp_path, "s2", [("user", "different content"), ("assistant", "mentions baz too")])
    hits = search_sessions("baz")
    assert len(hits) == 2
    ids = {h.session_id for h in hits}
    assert ids == {"s1", "s2"}


def test_case_insensitive(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [("user", "MixedCase Content")])
    hits = search_sessions("mixedcase")
    assert len(hits) == 1


def test_case_sensitive_flag(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [("user", "MixedCase Content")])
    assert search_sessions("mixedcase", case_insensitive=False) == []
    assert len(search_sessions("MixedCase", case_insensitive=False)) == 1


def test_role_filter(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [
        ("user", "token found"),
        ("assistant", "token found here"),
    ])
    user_hits = search_sessions("token", role_filter="user")
    assert len(user_hits) == 1
    assert user_hits[0].role == "user"


def test_max_results_limit(tmp_path):
    from cli.search import search_sessions
    for i in range(5):
        _make_session(tmp_path, f"s{i}", [("user", f"matches here {i}")])
    hits = search_sessions("matches", max_results=3)
    assert len(hits) == 3


def test_snippet_has_context(tmp_path):
    from cli.search import search_sessions
    long = "PREFIX " * 20 + "NEEDLE" + " SUFFIX" * 20
    _make_session(tmp_path, "s1", [("user", long)])
    hits = search_sessions("NEEDLE")
    assert len(hits) == 1
    assert "NEEDLE" in hits[0].snippet


def test_turn_index_counted_correctly(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [
        ("user", "turn 1 no match"),
        ("assistant", "turn 2 no match"),
        ("user", "turn 3 TARGET match"),
    ])
    hits = search_sessions("TARGET")
    assert len(hits) == 1
    assert hits[0].turn_index == 3


def test_format_results_no_hits(tmp_path):
    from cli.search import format_results
    text = format_results([], "missing")
    assert "no matches" in text.lower()
    assert "missing" in text


def test_format_results_with_hits(tmp_path):
    from cli.search import search_sessions, format_results
    _make_session(tmp_path, "s-abc-def", [("user", "hello token here")])
    hits = search_sessions("token")
    text = format_results(hits, "token")
    assert "hit(s)" in text or "1" in text
    assert "s-abc-de" in text


def test_multiple_hits_in_same_session(tmp_path):
    from cli.search import search_sessions
    _make_session(tmp_path, "s1", [
        ("user", "TARGET appears once"),
        ("assistant", "reply without the keyword"),
        ("user", "TARGET appears again"),
    ])
    hits = search_sessions("TARGET")
    assert len(hits) == 2
    assert hits[0].turn_index != hits[1].turn_index
