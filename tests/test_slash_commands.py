"""Tests for cli/slash_commands.py — REPL slash dispatcher."""
import sys
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path):
    from agent.session_manager import set_sessions_dir
    from coding_agent.memory.store import set_memory_dir, clear_all_memories
    set_sessions_dir(str(tmp_path / "sessions"))
    set_memory_dir(str(tmp_path / "memory"))
    yield
    clear_all_memories()


def _state(tmp_path, sid=None):
    from cli.slash_commands import SlashState
    from agent.session_manager import new_session_id
    sid = sid or new_session_id()
    return SlashState(session_id=sid, model="some/model", system_prompt="You are helpful.")


def test_non_slash_returns_unhandled(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("hello world", _state(tmp_path))
    assert result.handled is False


def test_exit():
    from cli.slash_commands import dispatch_slash, SlashState
    state = SlashState(session_id="x", model="m")
    result = dispatch_slash("/exit", state)
    assert result.should_exit is True


def test_quit_alias():
    from cli.slash_commands import dispatch_slash, SlashState
    result = dispatch_slash("/quit", SlashState(session_id="x", model="m"))
    assert result.should_exit is True


def test_model_shows_current_when_no_arg(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/model", _state(tmp_path))
    assert result.handled
    assert "some/model" in result.output


def test_model_switch(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/model new/repo", _state(tmp_path))
    assert result.handled
    assert result.new_model == "new/repo"


def test_history_empty_session(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/history", _state(tmp_path))
    assert "(no history" in result.output


def test_history_populated(tmp_path):
    from cli.slash_commands import dispatch_slash
    from agent.session_manager import save_turn, HistoryDict
    state = _state(tmp_path)
    save_turn(state.session_id, HistoryDict(role="user", content="hi"))
    save_turn(state.session_id, HistoryDict(role="assistant", content="hello"))
    result = dispatch_slash("/history", state)
    assert "user" in result.output
    assert "hi" in result.output


def test_save_exports_markdown(tmp_path):
    from cli.slash_commands import dispatch_slash
    from agent.session_manager import save_turn, HistoryDict
    state = _state(tmp_path)
    save_turn(state.session_id, HistoryDict(role="user", content="question"))
    save_turn(state.session_id, HistoryDict(role="assistant", content="answer"))
    out = tmp_path / "export.md"
    result = dispatch_slash(f"/save {out}", state)
    assert out.exists()
    content = out.read_text()
    assert "# mojopi session" in content
    assert "question" in content
    assert "answer" in content


def test_save_requires_path(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/save", _state(tmp_path))
    assert "usage" in result.output.lower()


def test_fork_copies_history(tmp_path):
    from cli.slash_commands import dispatch_slash
    from agent.session_manager import save_turn, load_session_history, HistoryDict
    state = _state(tmp_path)
    save_turn(state.session_id, HistoryDict(role="user", content="turn1"))
    save_turn(state.session_id, HistoryDict(role="assistant", content="reply1"))
    result = dispatch_slash("/fork", state)
    assert result.handled
    assert result.new_session_id is not None
    assert result.new_session_id != state.session_id
    forked_history = load_session_history(result.new_session_id)
    assert len(forked_history) == 2
    assert forked_history[0].content == "turn1"


def test_tokens_reports_count(tmp_path):
    from cli.slash_commands import dispatch_slash
    from agent.session_manager import save_turn, HistoryDict
    state = _state(tmp_path)
    save_turn(state.session_id, HistoryDict(role="user", content="x" * 400))
    result = dispatch_slash("/tokens", state)
    assert "token" in result.output.lower()
    # 400/4 = 100 content tokens (plus system prompt)
    import re
    m = re.search(r"\d+", result.output)
    assert m is not None
    assert int(m.group(0)) >= 100


def test_memory_list_empty(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/memory list", _state(tmp_path))
    assert "no memories" in result.output.lower()


def test_memory_add_and_list(tmp_path):
    from cli.slash_commands import dispatch_slash
    state = _state(tmp_path)
    r1 = dispatch_slash('/memory add "prefers pytest"', state)
    assert "added memory" in r1.output.lower()
    r2 = dispatch_slash("/memory list", state)
    assert "pytest" in r2.output


def test_memory_add_requires_text(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/memory add", _state(tmp_path))
    assert "usage" in result.output.lower()


def test_memory_forget_by_suffix(tmp_path):
    from cli.slash_commands import dispatch_slash
    state = _state(tmp_path)
    add_result = dispatch_slash('/memory add "test fact"', state)
    # Extract the suffix from output
    from coding_agent.memory.store import list_memories
    mems = list_memories()
    full_id = mems[0].id
    forget_result = dispatch_slash(f"/memory forget {full_id[-8:]}", state)
    assert "forgot" in forget_result.output.lower()
    assert len(list_memories()) == 0


def test_memory_forget_missing(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/memory forget nosuchid", _state(tmp_path))
    assert "no memory" in result.output.lower()


def test_unknown_slash(tmp_path):
    from cli.slash_commands import dispatch_slash
    result = dispatch_slash("/nonsense", _state(tmp_path))
    assert result.handled is True
    assert "unknown" in result.output.lower()


def test_help_text_lists_commands():
    from cli.slash_commands import help_text
    t = help_text()
    for cmd in ("/exit", "/model", "/history", "/save", "/fork", "/tokens", "/memory"):
        assert cmd in t
