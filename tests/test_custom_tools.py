import sys; sys.path.insert(0, "src")

def test_custom_tool_importable():
    from coding_agent.extensions import custom_tool
    assert hasattr(custom_tool, "wrap_python_tool")

def test_wrap_and_dispatch():
    from coding_agent.extensions.custom_tool import wrap_python_tool
    from coding_agent.extensions.registry import dispatch_registered_tool, clear_registry
    clear_registry()
    wrap_python_tool("echo_tool", lambda text: text, description="echoes text", schema_json='{"text": "string"}')
    result = dispatch_registered_tool("echo_tool", '{"text": "hello"}')
    assert result == "hello"
    clear_registry()

def test_wrap_returns_dict():
    from coding_agent.extensions.custom_tool import wrap_python_tool
    from coding_agent.extensions.registry import clear_registry
    clear_registry()
    d = wrap_python_tool("t2", lambda: "ok")
    assert isinstance(d, dict)
    assert d["name"] == "t2"
    clear_registry()

def test_tool_to_agent_tool_json():
    from coding_agent.extensions.custom_tool import wrap_python_tool, tool_to_agent_tool_json
    from coding_agent.extensions.registry import clear_registry
    import json
    clear_registry()
    wrap_python_tool("t3", lambda: None, description="test", schema_json='{}')
    j = tool_to_agent_tool_json("t3")
    d = json.loads(j)
    assert d["name"] == "t3"
    assert d["description"] == "test"
    clear_registry()

def test_dispatch_unknown_tool_raises():
    from coding_agent.extensions.registry import dispatch_registered_tool, clear_registry
    clear_registry()
    raised = False
    try:
        dispatch_registered_tool("nonexistent_xyz", "{}")
    except KeyError:
        raised = True
    assert raised
