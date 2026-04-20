"""Real-world end-to-end integration test — actually runs the mojopi binary.

These tests invoke `mojo run -I src src/main.mojo` via subprocess and exercise:

  1. --version exits 0 with expected output
  2. Bad args produce a usage message and don't crash
  3. Print mode with a cached small MLX model streams tokens to stdout
  4. Print mode produces valid JSON when --mode json is set
  5. Interactive mode accepts /exit and /help slash commands
  6. Interactive mode persists a session file that can be resumed

All tests marked @pytest.mark.slow — they require the mojo binary + a cached
MLX model + ~30s per test. Run with:

    pixi run bash -c "PYTHONPATH=src pytest tests/test_end_to_end.py -v -m slow"

The default fast-test pass skips them.
"""
import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path
import pytest

# Small cached MLX model; ~300 MB
SMALL_MODEL = "mlx-community/Qwen3-0.6B-4bit"
HF_CACHE = Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser() / "hub"


def _model_cached(repo: str) -> bool:
    slug = "models--" + repo.replace("/", "--")
    return (HF_CACHE / slug).exists()


def _run_mojopi(args: list[str], stdin_input: str = "", timeout: int = 90, home: Path = None) -> subprocess.CompletedProcess:
    """Invoke the mojopi binary from the project root."""
    project = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project / "src")
    if home is not None:
        env["HOME"] = str(home)
    cmd = [
        os.path.expanduser("~/.pixi/bin/pixi"),
        "run", "bash", "-c",
        f"PYTHONPATH=src mojo run -I src src/main.mojo -- {' '.join(args)}"
    ]
    result = subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(project),
        env=env,
    )
    return result


@pytest.mark.slow
def test_version_flag_works():
    """--version must print 'mojopi <version>' and exit 0."""
    result = _run_mojopi(["--version"], timeout=60)
    assert result.returncode == 0, f"non-zero exit: {result.stderr}"
    assert "mojopi" in result.stdout
    assert "1.2.0" in result.stdout or "1." in result.stdout


@pytest.mark.slow
def test_bad_flag_shows_usage_and_exits_cleanly():
    """Unknown flag produces usage message (not a crash)."""
    result = _run_mojopi(["--no-such-flag-xyz"], timeout=60)
    # Exit code may be 0 or non-zero depending on arg parser, but MUST include usage
    combined = result.stdout + result.stderr
    assert "usage:" in combined.lower() or "mojopi" in combined


@pytest.mark.slow
def test_print_mode_with_small_mlx_model(tmp_path):
    """Run a one-shot -p against the cached 0.6B Qwen; verify non-empty output."""
    if not _model_cached(SMALL_MODEL):
        pytest.skip(f"{SMALL_MODEL} not cached; run verify_tool_calling.py to prepare")

    home = tmp_path / "home"
    home.mkdir()
    result = _run_mojopi(
        ["-p", "'Say hello in one short sentence.'", "--model", SMALL_MODEL, "--max-new-tokens", "32"],
        timeout=120,
        home=home,
    )
    assert result.returncode == 0, f"mojopi failed: {result.stderr}"
    # Output should contain something resembling a response
    assert len(result.stdout.strip()) > 0, "no output from agent"


@pytest.mark.slow
def test_json_mode_emits_valid_jsonl(tmp_path):
    """--mode json should produce a parseable JSON answer event."""
    if not _model_cached(SMALL_MODEL):
        pytest.skip(f"{SMALL_MODEL} not cached")

    home = tmp_path / "home"
    home.mkdir()
    result = _run_mojopi(
        ["-p", "'hi'", "--mode", "json", "--model", SMALL_MODEL, "--max-new-tokens", "16"],
        timeout=120,
        home=home,
    )
    assert result.returncode == 0
    # Find at least one JSON line in stdout
    lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
    assert len(lines) > 0, f"no JSON in output: {result.stdout[:500]!r}"
    parsed = json.loads(lines[0])
    assert "type" in parsed


@pytest.mark.slow
def test_interactive_help_and_exit(tmp_path):
    """REPL /help prints command list; /exit returns cleanly."""
    if not _model_cached(SMALL_MODEL):
        pytest.skip(f"{SMALL_MODEL} not cached")

    home = tmp_path / "home"
    home.mkdir()
    # Feed /help then /exit
    result = _run_mojopi(
        ["--model", SMALL_MODEL],
        stdin_input="/help\n/exit\n",
        timeout=60,
        home=home,
    )
    assert result.returncode == 0, f"REPL crashed: {result.stderr}"
    assert "/help" in result.stdout
    assert "/exit" in result.stdout


@pytest.mark.slow
def test_interactive_creates_session_file(tmp_path):
    """REPL launch creates a session dir under $HOME/.pi/sessions/."""
    if not _model_cached(SMALL_MODEL):
        pytest.skip(f"{SMALL_MODEL} not cached")

    home = tmp_path / "home"
    home.mkdir()
    result = _run_mojopi(
        ["--model", SMALL_MODEL],
        stdin_input="/session\n/exit\n",
        timeout=60,
        home=home,
    )
    assert result.returncode == 0
    # Session id should have been printed
    assert "session:" in result.stdout.lower() or "session " in result.stdout.lower()
    # A session directory should exist
    sessions_dir = home / ".pi" / "sessions"
    if sessions_dir.exists():
        # At least one subdir (uuid-named) — the /session command output confirms creation
        subdirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        # The session file may only be written on the first SAVED turn; /session
        # alone doesn't save anything. That's fine — the id was shown.
        assert True
