"""Tests for cli/env_loader.py."""
import sys
import os
sys.path.insert(0, "src")
import pytest


def test_module_importable():
    from cli import env_loader
    assert hasattr(env_loader, "load_dotenv")
    assert hasattr(env_loader, "parse_env_file")
    assert hasattr(env_loader, "get_env_int")
    assert hasattr(env_loader, "get_env_bool")


def test_parse_env_file_missing(tmp_path):
    from cli.env_loader import parse_env_file
    assert parse_env_file(tmp_path / "nope.env") == {}


def test_parse_env_file_basic(tmp_path):
    from cli.env_loader import parse_env_file
    p = tmp_path / ".env"
    p.write_text("MOJOPI_MODEL=my/repo\nMOJOPI_MAX_NEW_TOKENS=128\n")
    result = parse_env_file(p)
    assert result["MOJOPI_MODEL"] == "my/repo"
    assert result["MOJOPI_MAX_NEW_TOKENS"] == "128"


def test_parse_env_file_ignores_comments_and_blanks(tmp_path):
    from cli.env_loader import parse_env_file
    p = tmp_path / ".env"
    p.write_text(
        "# a comment\n"
        "\n"
        "MOJOPI_MODEL=x\n"
        "# another comment\n"
        "MOJOPI_AUTO_MEMORY=1\n"
    )
    result = parse_env_file(p)
    assert result == {"MOJOPI_MODEL": "x", "MOJOPI_AUTO_MEMORY": "1"}


def test_parse_env_file_strips_quotes(tmp_path):
    from cli.env_loader import parse_env_file
    p = tmp_path / ".env"
    p.write_text('KEY1="double quoted"\nKEY2=\'single\'\nKEY3=bare\n')
    result = parse_env_file(p)
    assert result["KEY1"] == "double quoted"
    assert result["KEY2"] == "single"
    assert result["KEY3"] == "bare"


def test_parse_env_file_skips_invalid_keys(tmp_path):
    from cli.env_loader import parse_env_file
    p = tmp_path / ".env"
    p.write_text("1BAD=x\nGOOD=y\n-DASH=z\n")
    result = parse_env_file(p)
    assert result == {"GOOD": "y"}


def test_load_dotenv_cwd_overrides_user(tmp_path, monkeypatch):
    from cli.env_loader import load_dotenv
    user = tmp_path / ".pi" / ".env"
    user.parent.mkdir()
    user.write_text("MOJOPI_MODEL=user-model\n")
    cwd = tmp_path / ".env"
    cwd.write_text("MOJOPI_MODEL=cwd-model\n")
    monkeypatch.delenv("MOJOPI_MODEL", raising=False)
    load_dotenv(cwd_env=cwd, user_env=user)
    assert os.environ["MOJOPI_MODEL"] == "cwd-model"
    monkeypatch.delenv("MOJOPI_MODEL", raising=False)


def test_load_dotenv_existing_env_wins(tmp_path, monkeypatch):
    """By default, shell-set env vars are NOT overridden by .env."""
    from cli.env_loader import load_dotenv
    monkeypatch.setenv("MOJOPI_MODEL", "shell-model")
    cwd = tmp_path / ".env"
    cwd.write_text("MOJOPI_MODEL=file-model\n")
    user = tmp_path / ".pi" / ".env"
    load_dotenv(cwd_env=cwd, user_env=user)
    assert os.environ["MOJOPI_MODEL"] == "shell-model"


def test_load_dotenv_override_true(tmp_path, monkeypatch):
    from cli.env_loader import load_dotenv
    monkeypatch.setenv("MOJOPI_MODEL", "shell-model")
    cwd = tmp_path / ".env"
    cwd.write_text("MOJOPI_MODEL=file-model\n")
    user = tmp_path / ".pi" / ".env"
    load_dotenv(cwd_env=cwd, user_env=user, override=True)
    assert os.environ["MOJOPI_MODEL"] == "file-model"


def test_get_env_int_valid(monkeypatch):
    from cli.env_loader import get_env_int
    monkeypatch.setenv("TEST_INT", "42")
    assert get_env_int("TEST_INT") == 42


def test_get_env_int_invalid_returns_default(monkeypatch):
    from cli.env_loader import get_env_int
    monkeypatch.setenv("TEST_INT", "not-a-number")
    assert get_env_int("TEST_INT", default=99) == 99


def test_get_env_int_unset_returns_default(monkeypatch):
    from cli.env_loader import get_env_int
    monkeypatch.delenv("TEST_INT", raising=False)
    assert get_env_int("TEST_INT", default=7) == 7


def test_get_env_bool_truthy(monkeypatch):
    from cli.env_loader import get_env_bool
    for v in ("1", "true", "yes", "anything"):
        monkeypatch.setenv("TEST_BOOL", v)
        assert get_env_bool("TEST_BOOL") is True


def test_get_env_bool_falsy(monkeypatch):
    from cli.env_loader import get_env_bool
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv("TEST_BOOL", v)
        assert get_env_bool("TEST_BOOL") is False


def test_get_env_bool_unset(monkeypatch):
    from cli.env_loader import get_env_bool
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert get_env_bool("TEST_BOOL", default=False) is False
    assert get_env_bool("TEST_BOOL", default=True) is True


def test_show_active_empty(monkeypatch):
    from cli.env_loader import show_active
    for k in list(os.environ.keys()):
        if k.startswith("MOJOPI_"):
            monkeypatch.delenv(k, raising=False)
    text = show_active()
    assert "no MOJOPI_* vars set" in text or "(no" in text.lower()


def test_show_active_populated(monkeypatch):
    from cli.env_loader import show_active
    monkeypatch.setenv("MOJOPI_MODEL", "test/model")
    monkeypatch.setenv("MOJOPI_MAX_NEW_TOKENS", "256")
    text = show_active()
    assert "test/model" in text
    assert "256" in text
