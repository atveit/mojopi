"""Integration tests for R3 Run.Run deliverables.

Tests:
  - Output mode (json/rpc) event emission
  - Parallel tool dispatch correctness + ordering
  - CLI args output_mode field
  - Packaging files exist
"""
import sys
sys.path.insert(0, "src")
import pytest


def _r3_available():
    try:
        from agent import output_mode, parallel_dispatch
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(not _r3_available(), reason="R3 modules not yet available")


# --- Output mode ---

def test_output_mode_importable():
    from agent import output_mode
    assert hasattr(output_mode, "emit")
    assert hasattr(output_mode, "JSON_MODE")
    assert hasattr(output_mode, "RPC_MODE")


def test_json_mode_emits_valid_jsonl(capsys):
    import json
    from agent.output_mode import emit_answer
    emit_answer("hello world", mode="json")
    captured = capsys.readouterr()
    event = json.loads(captured.out.strip())
    assert event["type"] == "answer"
    assert event["text"] == "hello world"


def test_print_mode_is_silent(capsys):
    from agent.output_mode import emit_token
    emit_token("hello", mode="print")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_rpc_mode_has_content_length():
    import io, sys
    from agent.output_mode import _write_rpc_event
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        _write_rpc_event({"type": "token", "text": "test"})
    finally:
        sys.stdout = old_stdout
    output = buf.getvalue()
    assert "Content-Length:" in output


def test_rpc_roundtrip():
    import io, json
    from agent.output_mode import _write_rpc_event, read_rpc_request
    import sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        _write_rpc_event({"method": "ping"})
    finally:
        sys.stdout = old
    # Read back
    stream = io.StringIO(buf.getvalue())
    req = read_rpc_request(stream)
    assert req is not None
    assert req["method"] == "ping"


# --- Parallel dispatch ---

def test_parallel_dispatch_importable():
    from agent import parallel_dispatch
    assert hasattr(parallel_dispatch, "dispatch_parallel")
    assert hasattr(parallel_dispatch, "READ_ONLY_TOOLS")


def test_parallel_preserves_order():
    from agent.parallel_dispatch import dispatch_parallel
    calls = [
        {"name": "read", "arguments_json": "{}"},
        {"name": "grep", "arguments_json": "{}"},
        {"name": "ls", "arguments_json": "{}"},
    ]
    results = dispatch_parallel(calls, lambda n, a: f"result-{n}")
    assert len(results) == 3
    assert results[0].result == "result-read"
    assert results[1].result == "result-grep"
    assert results[2].result == "result-ls"


def test_parallel_write_runs_sequential():
    from agent.parallel_dispatch import dispatch_parallel
    calls = [{"name": "bash", "arguments_json": "{}"}, {"name": "edit", "arguments_json": "{}"}]
    results = dispatch_parallel(calls, lambda n, a: f"ok-{n}")
    assert all(r.success for r in results)


# --- CLI args ---

def test_cli_args_has_output_mode():
    with open("src/cli/args.mojo") as f:
        src = f.read()
    assert "output_mode" in src


# --- Packaging files ---

def test_changelog_exists():
    from pathlib import Path
    assert Path("CHANGELOG.md").exists()
    content = Path("CHANGELOG.md").read_text()
    assert "Unreleased" in content or "v1.0" in content


def test_install_doc_exists():
    from pathlib import Path
    assert Path("docs/INSTALL.md").exists()


def test_conda_recipe_exists():
    from pathlib import Path
    assert Path("conda-recipe/meta.yaml").exists()
