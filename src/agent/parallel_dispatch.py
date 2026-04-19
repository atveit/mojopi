"""Parallel tool dispatch for read-only tools.

Read-only tools (read, grep, find, ls) can be dispatched in parallel via
threading.Thread. Write tools (bash, edit, write) always run sequentially.
"""
from __future__ import annotations
import threading
import queue
from typing import Any

READ_ONLY_TOOLS = frozenset({"read", "grep", "find", "ls"})


def _is_read_only(tool_name: str) -> bool:
    return tool_name in READ_ONLY_TOOLS


class ToolResult:
    def __init__(self, tool_name: str, arguments_json: str, result: str = "", error: str = ""):
        self.tool_name = tool_name
        self.arguments_json = arguments_json
        self.result = result
        self.error = error
        self.success = not bool(error)


def _dispatch_one(tool_name: str, arguments_json: str, dispatch_fn) -> ToolResult:
    """Dispatch a single tool call synchronously."""
    try:
        result = dispatch_fn(tool_name, arguments_json)
        return ToolResult(tool_name, arguments_json, result=result)
    except Exception as e:
        return ToolResult(tool_name, arguments_json, error=str(e))


def dispatch_parallel(
    tool_calls: list[dict],
    dispatch_fn,
    max_workers: int = 4,
) -> list[ToolResult]:
    """Dispatch multiple tool calls, parallelising read-only ones.

    Args:
        tool_calls: list of {"name": str, "arguments_json": str}
        dispatch_fn: callable(name, arguments_json) -> str
        max_workers: max parallel threads for read-only tools

    Returns list of ToolResult in the SAME ORDER as tool_calls.
    Write tools (bash/edit/write) are always dispatched sequentially after
    any pending parallel read tasks complete.
    """
    results: list[ToolResult | None] = [None] * len(tool_calls)

    read_indices = [i for i, tc in enumerate(tool_calls) if _is_read_only(tc["name"])]
    write_indices = [i for i, tc in enumerate(tool_calls) if not _is_read_only(tc["name"])]

    # Parallel dispatch for read-only
    if read_indices:
        threads: list[threading.Thread] = []
        slot_results: dict[int, ToolResult] = {}
        lock = threading.Lock()

        def run(idx: int):
            tc = tool_calls[idx]
            r = _dispatch_one(tc["name"], tc["arguments_json"], dispatch_fn)
            with lock:
                slot_results[idx] = r

        for i, idx in enumerate(read_indices):
            if i < max_workers:
                t = threading.Thread(target=run, args=(idx,), daemon=True)
                threads.append(t)
                t.start()
            else:
                # Sequential fallback if over worker limit
                run(idx)

        for t in threads:
            t.join(timeout=30.0)

        for idx, r in slot_results.items():
            results[idx] = r

        # Fill any that timed out
        for idx in read_indices:
            if results[idx] is None:
                results[idx] = ToolResult(tool_calls[idx]["name"], tool_calls[idx]["arguments_json"],
                                          error="timeout")

    # Sequential dispatch for write tools
    for idx in write_indices:
        tc = tool_calls[idx]
        results[idx] = _dispatch_one(tc["name"], tc["arguments_json"], dispatch_fn)

    return [r for r in results if r is not None]


def dispatch_parallel_if_all_read_only(
    tool_calls: list[dict],
    dispatch_fn,
) -> list[ToolResult] | None:
    """Dispatch in parallel only if ALL tool calls are read-only.

    Returns list of ToolResult if parallel dispatch was used, None otherwise.
    Callers fall back to sequential dispatch when None is returned.
    """
    if not tool_calls:
        return []
    if all(_is_read_only(tc["name"]) for tc in tool_calls):
        return dispatch_parallel(tool_calls, dispatch_fn)
    return None
