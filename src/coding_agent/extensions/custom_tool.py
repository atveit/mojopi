from typing import Callable
from coding_agent.extensions.registry import register_tool, dispatch_registered_tool

def wrap_python_tool(name: str, fn: Callable, description: str = "", schema_json: str = "{}") -> dict:
    """Register a Python callable as an agent tool. Returns AgentTool-compatible dict."""
    register_tool(name, fn, description=description, schema_json=schema_json)
    return {"name": name, "description": description, "schema_json": schema_json}

def tool_to_agent_tool_json(name: str) -> str:
    """Return JSON representation of a registered tool for the AgentTool struct."""
    import json
    from coding_agent.extensions.registry import get_registered_tools
    tools = get_registered_tools()
    if name not in tools:
        raise KeyError(f"Tool '{name}' not registered")
    t = tools[name]
    return json.dumps({"name": name, "description": t["description"], "schema_json": t["schema_json"]})
