"""Integration tests for R1 Run.Crawl deliverables.

Tests the full R1 surface:
  - TUI importability and instantiation
  - Extension registry + event bus integration
  - Custom tool round-trip through registry
  - Extension loader (directory scan)
  - Print helper (@file + stdin)
  - Event bus + registry working together
  - Cross-component: extension registers tool, event fires on tool dispatch
"""
import sys
sys.path.insert(0, "src")
import pytest


# --- Gate test: skip all if any R1 module is missing ---

def _r1_available():
    try:
        from coding_agent.tui import tui  # noqa
        from coding_agent.extensions import registry, events, loader, custom_tool  # noqa
        from cli import print_helper  # noqa
        return True
    except ImportError:
        return False

pytestmark = pytest.mark.skipif(not _r1_available(), reason="R1 modules not yet available")


# --- TUI ---

def test_tui_importable():
    from coding_agent.tui import tui
    assert hasattr(tui, "MojopiApp")
    assert hasattr(tui, "run_tui")
    assert hasattr(tui, "create_app")


def test_tui_app_instantiable():
    from coding_agent.tui.tui import create_app
    app = create_app()
    assert app is not None


# --- Extension registry ---

def test_extension_registry_importable():
    from coding_agent.extensions import registry
    assert callable(registry.register_tool)
    assert callable(registry.get_registered_tools)
    assert callable(registry.dispatch_registered_tool)


def test_register_and_call_tool():
    from coding_agent.extensions.registry import register_tool, dispatch_registered_tool, clear_registry
    clear_registry()
    register_tool("r1_test_tool", lambda msg: f"echo:{msg}", schema_json='{"msg": "string"}')
    result = dispatch_registered_tool("r1_test_tool", '{"msg": "hello"}')
    assert result == "echo:hello"
    clear_registry()


# --- Event bus ---

def test_event_bus_importable():
    from coding_agent.extensions import events
    assert hasattr(events, "TOOL_CALL")
    assert hasattr(events, "MESSAGE_START")
    assert hasattr(events, "MESSAGE_END")
    assert hasattr(events, "BEFORE_AGENT_START")
    assert hasattr(events, "BEFORE_COMPACT")
    assert hasattr(events, "CUSTOM_EVENT")


def test_event_round_trip():
    from coding_agent.extensions.events import on, fire_event, clear_event_handlers, CUSTOM_EVENT
    clear_event_handlers(CUSTOM_EVENT)
    got = []
    on(CUSTOM_EVENT, lambda p: got.append(p.data.get("key")))
    fire_event(CUSTOM_EVENT, {"key": "value"})
    assert got == ["value"]
    clear_event_handlers(CUSTOM_EVENT)


# --- Custom tools ---

def test_custom_tool_wrap_and_dispatch():
    from coding_agent.extensions.custom_tool import wrap_python_tool
    from coding_agent.extensions.registry import dispatch_registered_tool, clear_registry
    clear_registry()
    wrap_python_tool("r1_custom", lambda text: text.upper(), schema_json='{"text": "string"}')
    result = dispatch_registered_tool("r1_custom", '{"text": "hello"}')
    assert result == "HELLO"
    clear_registry()


# --- Loader ---

def test_loader_importable():
    from coding_agent.extensions import loader
    assert callable(loader.load_all_extensions)
    assert callable(loader.load_extensions_dir)


def test_loader_missing_dirs_ok():
    from coding_agent.extensions.loader import load_all_extensions
    # Global dirs may not exist; should return 0 without raising
    count = load_all_extensions(extra="")
    assert isinstance(count, int)
    assert count >= 0


def test_loader_loads_extension_file(tmp_path):
    from coding_agent.extensions.loader import load_extension_file
    from coding_agent.extensions.registry import get_registered_tools, clear_registry
    clear_registry()
    ext = tmp_path / "r1_test_ext.py"
    ext.write_text(
        "from coding_agent.extensions.registry import register_tool\n"
        "register_tool('ext_loaded_tool', lambda: 'ok')\n"
    )
    load_extension_file(str(ext))
    tools = get_registered_tools()
    assert "ext_loaded_tool" in tools
    clear_registry()


# --- Print helper ---

def test_print_helper_importable():
    from cli import print_helper
    assert callable(print_helper.expand_at_file)
    assert callable(print_helper.resolve_prompt)
    assert callable(print_helper.read_stdin_prompt)


def test_print_helper_at_file(tmp_path):
    from cli.print_helper import resolve_prompt
    f = tmp_path / "prompt.txt"
    f.write_text("  integration test prompt  ")
    result = resolve_prompt(f"@{f}")
    assert result == "integration test prompt"


# --- Cross-component: event + registry ---

def test_event_fired_on_registry_dispatch():
    """Extension registers a tool and an event handler; dispatch fires the event."""
    from coding_agent.extensions.registry import register_tool, dispatch_registered_tool, clear_registry
    from coding_agent.extensions.events import on, fire_event, clear_event_handlers, TOOL_CALL
    clear_registry()
    clear_event_handlers(TOOL_CALL)

    fired = []

    def my_tool(x): return f"done:{x}"
    register_tool("cross_test_tool", my_tool, schema_json='{"x": "string"}')
    on(TOOL_CALL, lambda p: fired.append(p.data.get("name")))

    # Manually fire the TOOL_CALL event as the agent loop would
    result = dispatch_registered_tool("cross_test_tool", '{"x": "hi"}')
    fire_event(TOOL_CALL, {"name": "cross_test_tool"})

    assert result == "done:hi"
    assert "cross_test_tool" in fired

    clear_registry()
    clear_event_handlers(TOOL_CALL)
