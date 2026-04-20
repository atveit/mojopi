"""Auto-trigger parallel dispatch when the whole batch is read-only.

Loop can call `maybe_parallel_dispatch(calls, dispatch_fn)` unconditionally —
this module decides whether to run serially or in parallel.
"""
from __future__ import annotations
import time
from typing import Callable

from agent.parallel_dispatch import (
    dispatch_parallel, ToolResult, READ_ONLY_TOOLS, _is_read_only,
)


def all_read_only(calls: list[dict]) -> bool:
    """True iff every call's tool name is in READ_ONLY_TOOLS."""
    if not calls:
        return True
    return all(_is_read_only(c.get("name", "")) for c in calls)


def maybe_parallel_dispatch(
    calls: list[dict],
    dispatch_fn: Callable[[str, str], str],
    min_batch_size: int = 2,
) -> list[ToolResult]:
    """Dispatch a batch of tool calls.

    - If the batch is entirely read-only AND has >= min_batch_size entries,
      dispatch in parallel via agent.parallel_dispatch.
    - Otherwise dispatch sequentially in the original order.

    Returns a list of ToolResult in the same order as the input calls.

    Each call dict must have `{"name": str, "arguments_json": str}` shape.
    If a call is missing those keys, it's dispatched sequentially with an
    error result.
    """
    if not calls:
        return []

    # Normalize shape
    normalized = []
    for c in calls:
        normalized.append({
            "name": c.get("name", ""),
            "arguments_json": c.get("arguments_json", c.get("arguments", "{}")),
        })

    if len(normalized) >= min_batch_size and all_read_only(normalized):
        return dispatch_parallel(normalized, dispatch_fn)

    # Sequential fallback
    results = []
    for call in normalized:
        try:
            r = dispatch_fn(call["name"], call["arguments_json"])
            results.append(ToolResult(
                tool_name=call["name"],
                arguments_json=call["arguments_json"],
                result=r,
            ))
        except Exception as e:
            results.append(ToolResult(
                tool_name=call["name"],
                arguments_json=call["arguments_json"],
                error=str(e),
            ))
    return results


def benchmark_parallel_vs_sequential(
    n_calls: int = 3,
    call_delay: float = 0.05,
) -> dict:
    """Contrived benchmark: n_calls × call_delay seconds each.

    Returns {"sequential_s": float, "parallel_s": float, "speedup": float}.
    """
    calls = [{"name": "read", "arguments_json": f'{{"path": "f{i}"}}'} for i in range(n_calls)]

    def slow(name: str, args: str) -> str:
        time.sleep(call_delay)
        return f"r-{name}"

    t0 = time.perf_counter()
    _ = maybe_parallel_dispatch(calls, slow, min_batch_size=n_calls + 1)  # force serial
    seq = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = maybe_parallel_dispatch(calls, slow, min_batch_size=2)
    par = time.perf_counter() - t0

    return {
        "sequential_s": round(seq, 3),
        "parallel_s": round(par, 3),
        "speedup": round(seq / par if par > 0 else 0, 2),
        "n_calls": n_calls,
        "call_delay": call_delay,
    }
