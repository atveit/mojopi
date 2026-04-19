"""Tool hook registry for the mojopi agent loop.

Hooks are Python callables. before_tool_call hooks receive (tool_name, arguments_json)
and can return a modified arguments_json or None (no change).
after_tool_call hooks receive (tool_name, arguments_json, result) and can return
a modified result or None (no change).

All hooks are called in registration order. Exceptions in hooks are caught and logged
(never propagate to the agent loop).
"""
from typing import Callable, Any

# List of (name, callable) pairs.
_before_hooks: list[tuple[str, Callable]] = []
_after_hooks: list[tuple[str, Callable]] = []


def register_before_tool_call(hook: Callable, name: str = "") -> None:
    """Register a before_tool_call hook. Called before each tool dispatch."""
    _before_hooks.append((name or repr(hook), hook))


def register_after_tool_call(hook: Callable, name: str = "") -> None:
    """Register an after_tool_call hook. Called after each tool dispatch."""
    _after_hooks.append((name or repr(hook), hook))


def clear_hooks() -> None:
    """Remove all registered hooks (useful in tests)."""
    _before_hooks.clear()
    _after_hooks.clear()


def run_before_hooks(tool_name: str, arguments_json: str) -> str:
    """Run all before hooks. Returns (possibly modified) arguments_json."""
    args = arguments_json
    for hook_name, hook in _before_hooks:
        try:
            result = hook(tool_name, args)
            if isinstance(result, str):
                args = result
        except Exception as e:
            print(f"[hooks] before_tool_call hook '{hook_name}' raised: {e}")
    return args


def run_after_hooks(tool_name: str, arguments_json: str, result: str) -> str:
    """Run all after hooks. Returns (possibly modified) result string."""
    r = result
    for hook_name, hook in _after_hooks:
        try:
            new_r = hook(tool_name, arguments_json, r)
            if isinstance(new_r, str):
                r = new_r
        except Exception as e:
            print(f"[hooks] after_tool_call hook '{hook_name}' raised: {e}")
    return r


def hook_count() -> dict[str, int]:
    """Return counts of registered hooks by type."""
    return {"before": len(_before_hooks), "after": len(_after_hooks)}
