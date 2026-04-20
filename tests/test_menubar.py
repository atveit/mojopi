"""Tests for coding_agent/ui/menubar — structural only, no NSApp."""
import sys
sys.path.insert(0, "src")
import pytest


def test_module_importable():
    from coding_agent.ui.menubar import menubar
    assert hasattr(menubar, "build_app")
    assert hasattr(menubar, "_run_mojopi")
    assert hasattr(menubar, "_recent_sessions")


def test_build_app_returns_rumps_app():
    from coding_agent.ui.menubar.menubar import build_app
    app = build_app(run_mojopi_fn=lambda *a, **k: "stub answer")
    # rumps.App has a .title attribute
    assert hasattr(app, "title")


def test_build_app_has_menu_items():
    from coding_agent.ui.menubar.menubar import build_app
    app = build_app(run_mojopi_fn=lambda *a, **k: "stub")
    # The app.menu dict should have the items we added
    titles = [str(k) for k in app.menu.keys()]
    assert "Ask mojopi…" in titles
    assert "Recent sessions" in titles
    assert "Settings" in titles
    assert "Quit mojopi" in titles


def test_build_app_state_holds_model_and_tokens():
    from coding_agent.ui.menubar.menubar import build_app
    app = build_app(model="custom/model", max_tokens=999, run_mojopi_fn=lambda *a, **k: "x")
    assert app._mojopi_state["model"] == "custom/model"
    assert app._mojopi_state["max_tokens"] == 999


def test_recent_sessions_empty(tmp_path, monkeypatch):
    from coding_agent.ui.menubar import menubar
    monkeypatch.setenv("HOME", str(tmp_path))
    # _recent_sessions uses Path("~/.pi/sessions").expanduser() which reads HOME
    assert menubar._recent_sessions() == []


def test_recent_sessions_finds_real_ones(tmp_path, monkeypatch):
    from coding_agent.ui.menubar import menubar
    monkeypatch.setenv("HOME", str(tmp_path))
    s = tmp_path / ".pi" / "sessions" / "abc-123"
    s.mkdir(parents=True)
    (s / "transcript.jsonl").write_text('{"type":"message"}\n')
    results = menubar._recent_sessions()
    assert len(results) == 1
    assert results[0][0] == "abc-123"


def test_project_root_locates_pixi_toml():
    from coding_agent.ui.menubar.menubar import _project_root
    root = _project_root()
    assert (root / "pixi.toml").exists()
