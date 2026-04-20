"""Tests for cli/repl_helper.py — REPL rendering, env var defaults, /file."""
import sys, os
sys.path.insert(0, "src")


def test_module_importable():
    from cli import repl_helper
    assert hasattr(repl_helper, "render_response")
    assert hasattr(repl_helper, "env_model_default")
    assert hasattr(repl_helper, "env_max_new_tokens_default")
    assert hasattr(repl_helper, "read_file_for_slash_command")
    assert hasattr(repl_helper, "welcome_banner")


def test_welcome_banner_contains_version():
    from cli.repl_helper import welcome_banner
    b = welcome_banner("1.0.1")
    assert "1.0.1" in b
    assert "mojopi" in b


def test_env_model_default_returns_string():
    from cli.repl_helper import env_model_default
    assert isinstance(env_model_default(), str)


def test_env_model_default_reads_env(monkeypatch):
    from cli.repl_helper import env_model_default
    monkeypatch.setenv("MOJOPI_MODEL", "custom/model")
    assert env_model_default() == "custom/model"


def test_env_tokens_default_reads_env(monkeypatch):
    from cli.repl_helper import env_max_new_tokens_default
    monkeypatch.setenv("MOJOPI_MAX_NEW_TOKENS", "128")
    assert env_max_new_tokens_default() == 128


def test_env_tokens_default_invalid_returns_zero(monkeypatch):
    from cli.repl_helper import env_max_new_tokens_default
    monkeypatch.setenv("MOJOPI_MAX_NEW_TOKENS", "not_a_number")
    assert env_max_new_tokens_default() == 0


def test_env_tokens_default_unset_returns_zero(monkeypatch):
    from cli.repl_helper import env_max_new_tokens_default
    monkeypatch.delenv("MOJOPI_MAX_NEW_TOKENS", raising=False)
    assert env_max_new_tokens_default() == 0


def test_read_file_for_slash_command(tmp_path):
    from cli.repl_helper import read_file_for_slash_command
    f = tmp_path / "note.txt"
    f.write_text("hello from file")
    assert read_file_for_slash_command(str(f)) == "hello from file"


def test_read_file_missing_raises(tmp_path):
    from cli.repl_helper import read_file_for_slash_command
    import pytest
    with pytest.raises(FileNotFoundError):
        read_file_for_slash_command("/tmp/does_not_exist_mojopi_xyz.txt")


def test_render_response_does_not_raise(capsys):
    from cli.repl_helper import render_response
    render_response("# Hello\n\nsome **markdown** with `code`.")
    out = capsys.readouterr().out
    assert "Hello" in out
