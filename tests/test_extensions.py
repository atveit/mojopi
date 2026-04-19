import sys; sys.path.insert(0, "src")

def test_events_importable():
    from coding_agent.extensions import events
    assert hasattr(events, "fire_event")
    assert hasattr(events, "on")
    assert hasattr(events, "TOOL_CALL")

def test_event_fire_calls_handler():
    from coding_agent.extensions.events import on, fire_event, clear_event_handlers, TOOL_CALL
    clear_event_handlers(TOOL_CALL)
    received = []
    on(TOOL_CALL, lambda p: received.append(p.event_type))
    fire_event(TOOL_CALL, {"name": "read"})
    assert received == [TOOL_CALL]
    clear_event_handlers(TOOL_CALL)

def test_event_handler_exception_doesnt_propagate():
    from coding_agent.extensions.events import on, fire_event, clear_event_handlers, MESSAGE_START
    clear_event_handlers(MESSAGE_START)
    def bad_handler(p):
        raise RuntimeError("boom")
    on(MESSAGE_START, bad_handler)
    # Should not raise
    fire_event(MESSAGE_START)
    clear_event_handlers(MESSAGE_START)

def test_registry_importable():
    from coding_agent.extensions import registry
    assert hasattr(registry, "register_tool")
    assert hasattr(registry, "get_registered_tools")

def test_registry_register_and_dispatch():
    from coding_agent.extensions.registry import register_tool, dispatch_registered_tool, clear_registry
    clear_registry()
    register_tool("my_tool", lambda x: f"result:{x}", schema_json='{"x": "string"}')
    result = dispatch_registered_tool("my_tool", '{"x": "hello"}')
    assert result == "result:hello"
    clear_registry()

def test_loader_importable():
    from coding_agent.extensions import loader
    assert hasattr(loader, "load_all_extensions")
    assert hasattr(loader, "load_extensions_dir")

def test_loader_missing_dir_returns_zero():
    from coding_agent.extensions.loader import load_extensions_dir
    count = load_extensions_dir("/tmp/does_not_exist_xyz_mojopi")
    assert count == 0

def test_loader_loads_py_file(tmp_path):
    from coding_agent.extensions.loader import load_extension_file
    ext = tmp_path / "my_ext.py"
    ext.write_text("_loaded = True\n")
    load_extension_file(str(ext))  # should not raise

def test_handler_count():
    from coding_agent.extensions.events import on, handler_count, clear_event_handlers, BEFORE_COMPACT
    clear_event_handlers(BEFORE_COMPACT)
    assert handler_count(BEFORE_COMPACT) == 0
    on(BEFORE_COMPACT, lambda p: None)
    assert handler_count(BEFORE_COMPACT) == 1
    clear_event_handlers(BEFORE_COMPACT)

def test_clear_all_handlers():
    from coding_agent.extensions.events import on, handler_count, clear_event_handlers, TOOL_CALL, MESSAGE_END
    on(TOOL_CALL, lambda p: None)
    on(MESSAGE_END, lambda p: None)
    clear_event_handlers()
    assert handler_count(TOOL_CALL) == 0
    assert handler_count(MESSAGE_END) == 0
