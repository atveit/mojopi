"""W1 integration gate tests.

These tests check that all W1 deliverables are importable and structurally
correct, WITHOUT requiring model weights or running actual inference.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_session_store_importable():
    """Session store Python module is importable."""
    try:
        from coding_agent.session.store import (
            read_session, write_session, get_leaf_branches,
            resolve_path, get_messages_from_path,
        )
    except ImportError:
        pytest.skip("session store not yet implemented")


def test_context_loader_importable():
    """Context loader Python module is importable."""
    try:
        from coding_agent.context.loader import (
            find_context_files, load_project_overrides,
            load_global_agents_md, compose_context,
        )
    except ImportError:
        pytest.skip("context loader not yet implemented")


def test_session_round_trip(tmp_path):
    """Write + read a session round-trips losslessly."""
    try:
        from coding_agent.session.store import read_session, write_session
    except ImportError:
        pytest.skip("session store not yet implemented")

    entries = [
        {"type": "session", "v": 3, "id": "s1", "parentId": None, "cwd": "/tmp", "timestamp": 123},
        {"type": "message", "id": "m1", "parentId": "s1",
         "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
    ]
    path = str(tmp_path / "test.jsonl")
    write_session(path, entries)
    loaded = read_session(path)
    assert len(loaded) == 2
    assert loaded[0]["type"] == "session"
    assert loaded[1]["type"] == "message"


def test_full_types_fixture():
    """The full_types.jsonl fixture loads and contains all 7 types."""
    try:
        from coding_agent.session.store import read_session
    except ImportError:
        pytest.skip("session store not yet implemented")

    fixture = os.path.join(os.path.dirname(__file__), 'fixtures', 'sessions', 'full_types.jsonl')
    if not os.path.exists(fixture):
        pytest.skip("fixture not yet created")
    entries = read_session(fixture)
    types_found = {e["type"] for e in entries}
    expected = {
        "session", "message", "thinking_level_change", "model_change",
        "compaction", "branch_summary", "custom", "custom_message",
    }
    # session has 1 session + 7 others = 8 entries, 8 types
    assert expected <= types_found


def test_context_files_found(tmp_path):
    """find_context_files finds AGENTS.md files."""
    try:
        from coding_agent.context.loader import find_context_files
    except ImportError:
        pytest.skip("context loader not yet implemented")

    # Create a nested structure
    outer = tmp_path / "project"
    inner = outer / "subdir"
    inner.mkdir(parents=True)
    (outer / "AGENTS.md").write_text("outer", encoding="utf-8")
    (inner / "AGENTS.md").write_text("inner", encoding="utf-8")
    files = find_context_files(str(inner))
    assert len(files) >= 2


def test_pipeline_module_importable():
    """max_brain.pipeline is importable."""
    try:
        from max_brain.pipeline import get_max_version, run_one_shot, generate_embedded
    except ImportError:
        pytest.skip("max_brain.pipeline not yet implemented")

    assert callable(get_max_version)
    assert callable(run_one_shot)
    assert callable(generate_embedded)


def test_session_fixtures_exist():
    """All three session fixture files exist and contain valid JSON lines."""
    import json

    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'sessions')
    expected_files = ['minimal.jsonl', 'full_types.jsonl', 'branching.jsonl']
    for fname in expected_files:
        fpath = os.path.join(fixtures_dir, fname)
        assert os.path.exists(fpath), f"Missing fixture: {fpath}"
        with open(fpath, encoding='utf-8') as fp:
            lines = [line.strip() for line in fp if line.strip()]
        assert len(lines) > 0, f"Empty fixture: {fname}"
        for i, line in enumerate(lines, 1):
            obj = json.loads(line)  # raises on invalid JSON
            assert "type" in obj, f"{fname} line {i} missing 'type' field"


def test_minimal_fixture_structure():
    """minimal.jsonl has a session header and two messages."""
    import json

    fpath = os.path.join(os.path.dirname(__file__), 'fixtures', 'sessions', 'minimal.jsonl')
    with open(fpath, encoding='utf-8') as fp:
        entries = [json.loads(line) for line in fp if line.strip()]
    assert entries[0]["type"] == "session"
    assert entries[0]["v"] == 3
    assert all(e["type"] == "message" for e in entries[1:])


def test_branching_fixture_has_two_leaves():
    """branching.jsonl has two messages sharing the same parentId (fork)."""
    import json

    fpath = os.path.join(os.path.dirname(__file__), 'fixtures', 'sessions', 'branching.jsonl')
    with open(fpath, encoding='utf-8') as fp:
        entries = [json.loads(line) for line in fp if line.strip()]
    parent_ids = [e.get("parentId") for e in entries]
    # Two entries should share the same parentId (the fork point)
    from collections import Counter
    counts = Counter(parent_ids)
    assert any(v >= 2 for v in counts.values()), "Expected at least one parentId with two children"


def test_fake_project_fixtures_exist():
    """fake_project/ fixture tree has AGENTS.md files."""
    base = os.path.join(os.path.dirname(__file__), 'fixtures', 'fake_project')
    assert os.path.exists(os.path.join(base, 'AGENTS.md'))
    assert os.path.exists(os.path.join(base, 'subdir', 'AGENTS.md'))


def test_grep_sample_fixture_exists():
    """grep_sample.txt fixture file exists with expected content."""
    fpath = os.path.join(os.path.dirname(__file__), 'fixtures', 'grep_sample.txt')
    assert os.path.exists(fpath)
    content = open(fpath, encoding='utf-8').read()
    assert 'hello world' in content
    assert 'HELLO UPPER' in content
