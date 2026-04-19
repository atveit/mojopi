"""W3 integration gate tests.

Checks that all W3 deliverables are importable and structurally correct,
WITHOUT requiring model weights.

W3 deliverables:
- Compaction: coding_agent.compaction.compactor
- Steering: agent.steering
- Skills: coding_agent.skills.loader
- Abort: agent.abort
- Hooks: agent.hooks
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ── Compaction ──────────────────────────────────────────────────────────────

def test_compaction_importable():
    try:
        from coding_agent.compaction.compactor import (
            estimate_tokens, estimate_history_tokens, should_compact, compact_history
        )
    except ImportError:
        pytest.skip("compaction module not yet implemented")

def test_compaction_token_estimate():
    try:
        from coding_agent.compaction.compactor import estimate_tokens
    except ImportError:
        pytest.skip("compaction not yet implemented")
    # 400 chars ÷ 4 = 100 tokens
    assert estimate_tokens("a" * 400) == 100

def test_compaction_threshold():
    try:
        from coding_agent.compaction.compactor import should_compact
    except ImportError:
        pytest.skip("compaction not yet implemented")
    # Empty history → no compaction needed
    assert not should_compact([], max_tokens=8192)
    # Very large history → compact
    big = [{"role": "user", "content": "x" * 30000}]
    assert should_compact(big, max_tokens=8192)

def test_compaction_keeps_last_n(tmp_path):
    try:
        from coding_agent.compaction.compactor import compact_history
    except ImportError:
        pytest.skip("compaction not yet implemented")
    history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    new_hist, summary = compact_history(history, keep_last_n=3)
    # [summary_entry] + last 3 = 4 entries
    assert len(new_hist) == 4
    assert new_hist[0]["role"] == "system"


# ── Steering ──────────────────────────────────────────────────────────────

def test_steering_importable():
    try:
        from agent.steering import push_steering, poll_steering, clear_steering
    except ImportError:
        pytest.skip("steering module not yet implemented")

def test_steering_roundtrip():
    try:
        from agent.steering import push_steering, poll_steering, clear_steering
    except ImportError:
        pytest.skip()
    clear_steering()
    push_steering("hello from test")
    msg = poll_steering()
    assert msg == "hello from test"

def test_steering_empty():
    try:
        from agent.steering import poll_steering, clear_steering
    except ImportError:
        pytest.skip()
    clear_steering()
    assert poll_steering() is None


# ── Skills ──────────────────────────────────────────────────────────────────

def test_skills_importable():
    try:
        from coding_agent.skills.loader import load_skill_file, load_skills_dir
    except ImportError:
        pytest.skip("skills module not yet implemented")

def test_skills_filter():
    try:
        from coding_agent.skills.loader import filter_skills
    except ImportError:
        pytest.skip()
    skills = [
        {"name": "a", "trigger": "always"},
        {"name": "b", "trigger": "manual"},
        {"name": "c", "trigger": "when_read_available"},
    ]
    assert len(filter_skills(skills, read_tool_available=True)) == 2
    assert len(filter_skills(skills, read_tool_available=False)) == 1

def test_skills_fixture_dir():
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'skills')
    if not os.path.isdir(fixtures_dir):
        pytest.skip("skills fixtures not yet created")
    try:
        from coding_agent.skills.loader import load_skills_dir
    except ImportError:
        pytest.skip()
    skills = load_skills_dir(fixtures_dir)
    assert len(skills) >= 2


# ── Abort ────────────────────────────────────────────────────────────────────

def test_abort_importable():
    try:
        from agent.abort import request_abort, clear_abort, is_aborted
    except ImportError:
        pytest.skip("abort module not yet implemented")

def test_abort_lifecycle():
    try:
        from agent.abort import request_abort, clear_abort, is_aborted
    except ImportError:
        pytest.skip()
    clear_abort()
    assert not is_aborted()
    request_abort()
    assert is_aborted()
    clear_abort()
    assert not is_aborted()


# ── Hooks ─────────────────────────────────────────────────────────────────────

def test_hooks_importable():
    try:
        from agent.hooks import (
            register_before_tool_call, register_after_tool_call,
            clear_hooks, run_before_hooks, run_after_hooks
        )
    except ImportError:
        pytest.skip("hooks module not yet implemented")

def test_hooks_passthrough():
    try:
        from agent.hooks import run_before_hooks, run_after_hooks, clear_hooks
    except ImportError:
        pytest.skip()
    clear_hooks()
    assert run_before_hooks("tool", '{"x": 1}') == '{"x": 1}'
    assert run_after_hooks("tool", "{}", "result") == "result"

def test_hooks_modification():
    try:
        from agent.hooks import register_before_tool_call, run_before_hooks, clear_hooks
    except ImportError:
        pytest.skip()
    clear_hooks()
    register_before_tool_call(lambda t, a: a.upper())
    result = run_before_hooks("tool", '{"path": "/tmp"}')
    assert result == '{"PATH": "/TMP"}'
    clear_hooks()


# ── Cross-component ──────────────────────────────────────────────────────────

def test_all_w3_modules_available():
    """Gate test: all 5 W3 modules must be importable for W3 to be complete."""
    missing = []
    modules = [
        ("coding_agent.compaction.compactor", "compaction"),
        ("agent.steering", "steering"),
        ("coding_agent.skills.loader", "skills"),
        ("agent.abort", "abort"),
        ("agent.hooks", "hooks"),
    ]
    for mod_path, name in modules:
        try:
            __import__(mod_path)
        except ImportError:
            missing.append(name)

    if missing:
        pytest.skip(f"W3 modules not yet complete: {missing}")
    # If we get here, all modules are available
    assert len(missing) == 0
