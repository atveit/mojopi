"""macOS menu bar app using rumps (AppKit-native Python framework).

Click the 🤖 icon → "Ask mojopi" opens a Cocoa input dialog → output shown
in an alert. Recent sessions and settings menus supported.

Launch:
    pixi run python -m coding_agent.ui.menubar.menubar

Requires macOS and the `rumps` pip package.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

TITLE = "🤖"
DEFAULT_MODEL = os.environ.get("MOJOPI_MODEL", "mlx-community/gemma-4-e4b-it-4bit")
DEFAULT_MAX_TOKENS = int(os.environ.get("MOJOPI_MAX_NEW_TOKENS", "128"))


def _project_root() -> Path:
    """Locate the mojopi project root (looks up from this file)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pixi.toml").exists():
            return parent
    return Path.cwd()


def _run_mojopi(prompt: str, model: str, max_tokens: int, timeout: int = 120) -> str:
    """Spawn mojopi -p and return the answer text.

    Uses --mode json so we get a parseable {"type": "answer", "text": "..."} event.
    """
    root = _project_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    cmd = [
        os.path.expanduser("~/.pixi/bin/pixi"),
        "run", "bash", "-c",
        f"PYTHONPATH=src mojo run -I src src/main.mojo -- "
        f"-p '{prompt.replace(chr(39), chr(92) + chr(39))}' "
        f"--mode json --model {model} --max-new-tokens {max_tokens}",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(root), env=env,
        )
    except subprocess.TimeoutExpired:
        return "(mojopi timed out)"
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                event = json.loads(line)
                if event.get("type") == "answer":
                    return event.get("text", "(empty answer)")
            except json.JSONDecodeError:
                continue
    return result.stdout[-2000:] or result.stderr[-1000:] or "(no output)"


def _recent_sessions(limit: int = 5) -> list[tuple[str, float]]:
    """Return [(session_id, mtime)] for the most recently modified sessions."""
    sessions_dir = Path("~/.pi/sessions").expanduser()
    if not sessions_dir.exists():
        return []
    results = []
    for child in sessions_dir.iterdir():
        if child.is_dir() and (child / "transcript.jsonl").exists():
            results.append((child.name, (child / "transcript.jsonl").stat().st_mtime))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def build_app(
    title: str = TITLE,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    run_mojopi_fn=None,
):
    """Construct and return the rumps.App without starting the event loop.

    Separated from `main()` so tests can inspect the menu structure without
    actually launching a NSApp instance.
    """
    import rumps

    if run_mojopi_fn is None:
        run_mojopi_fn = _run_mojopi

    state = {
        "model": model,
        "max_tokens": max_tokens,
    }

    app = rumps.App(title, quit_button=None)

    ask = rumps.MenuItem("Ask mojopi…", key="a")
    recent_menu = rumps.MenuItem("Recent sessions")
    settings_menu = rumps.MenuItem("Settings")
    model_item = rumps.MenuItem(f"Model: {state['model'].split('/')[-1]}")
    tokens_item = rumps.MenuItem(f"Max tokens: {state['max_tokens']}")
    settings_menu.update([model_item, tokens_item])
    quit_item = rumps.MenuItem("Quit mojopi", key="q")

    def _on_ask(_):
        window = rumps.Window(
            title="Ask mojopi",
            message="Enter your prompt:",
            default_text="",
            ok="Send",
            cancel="Cancel",
            dimensions=(320, 160),
        )
        resp = window.run()
        if not resp.clicked or not resp.text.strip():
            return
        answer = run_mojopi_fn(resp.text.strip(), state["model"], state["max_tokens"])
        rumps.alert(title="mojopi", message=answer[:800])

    def _refresh_recent():
        # Ensure the sub-menu exists; `.update([])` creates the NSMenu backing
        # so subsequent `.clear()` / `.add()` calls work even if the item has
        # not yet been attached to the app's root menu.
        if recent_menu._menu is None:
            recent_menu.update([])
        else:
            recent_menu.clear()
        sessions = _recent_sessions()
        if not sessions:
            recent_menu.add(rumps.MenuItem("(no sessions yet)"))
            return
        for sid, mtime in sessions:
            item = rumps.MenuItem(f"{sid[:8]}")
            recent_menu.add(item)

    def _on_quit(_):
        import rumps
        rumps.quit_application()

    ask.set_callback(_on_ask)
    quit_item.set_callback(_on_quit)

    _refresh_recent()

    app.menu = [ask, recent_menu, settings_menu, None, quit_item]

    # Expose internals for tests
    app._mojopi_state = state
    app._mojopi_ask_callback = _on_ask
    app._mojopi_refresh_recent = _refresh_recent

    return app


def main():
    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
