from typing import Callable, Any
from agent.hooks import register_before_tool_call, register_after_tool_call, clear_hooks

_registered_tools: dict[str, dict] = {}  # name → {fn, description, schema_json}
_registered_commands: dict[str, Callable] = {}

def register_tool(name: str, fn: Callable, description: str = "", schema_json: str = "{}") -> None:
    _registered_tools[name] = {"fn": fn, "description": description, "schema_json": schema_json}

def register_command(name: str, fn: Callable) -> None:
    _registered_commands[name] = fn

def get_registered_tools() -> dict:
    return dict(_registered_tools)

def get_registered_commands() -> dict:
    return dict(_registered_commands)

def dispatch_registered_tool(name: str, arguments_json: str) -> str:
    """Dispatch a registered Python tool. Raises KeyError if not found."""
    import json
    if name not in _registered_tools:
        raise KeyError(f"No registered tool named '{name}'")
    fn = _registered_tools[name]["fn"]
    args = json.loads(arguments_json) if arguments_json.strip() else {}
    result = fn(**args) if isinstance(args, dict) else fn(args)
    return str(result) if result is not None else ""

def clear_registry() -> None:
    _registered_tools.clear()
    _registered_commands.clear()

def tool_count() -> int:
    return len(_registered_tools)
