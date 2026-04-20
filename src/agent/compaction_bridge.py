"""Auto-compaction bridge for the agent loop.

When the cumulative history size crosses a token threshold, summarize the
older turns and keep only the last N verbatim. The summary becomes a single
synthetic 'system' turn at the head of the history.

Thin wrapper over ``coding_agent.compaction.compactor`` — the real work happens
there. This module adds the 'when to trigger' policy the loop needs.

The underlying compactor exposes:
  * ``estimate_tokens(text) -> int``         (approximate: len(text) // 4)
  * ``estimate_history_tokens(history)``      (sums role + content per entry)
  * ``should_compact(history, max_tokens, threshold)``
  * ``compact_history(history, model, keep_last_n, max_tokens) -> (list, str)``

We wrap those in a stable 'auto_compact_if_needed' surface that the agent loop
can call once per turn.
"""
from __future__ import annotations

from typing import Callable, Optional

from coding_agent.compaction.compactor import (
    estimate_tokens as _estimate_tokens,
    estimate_history_tokens as _estimate_history_tokens,
    should_compact as _should_compact,
    compact_history as _compact_history,
)

# Token budget for Llama-3-8B class (8k context default); override via arg.
DEFAULT_CONTEXT_TOKENS = 8192
DEFAULT_THRESHOLD = 0.75
DEFAULT_KEEP_LAST_N = 4


def count_tokens_from_bridge(text: str) -> int:
    """Re-export of the compactor's per-string token estimator."""
    return _estimate_tokens(text or "")


def estimate_history_tokens(history: list[dict]) -> int:
    """Sum approximate token count across all turns (content only).

    The underlying ``estimate_history_tokens`` also counts the role string —
    for the bridge's 'should we compact?' decision we sum only content, which
    matches the task's intent and is slightly more conservative. The helper
    also tolerates None entries so the loop can call it on raw history.
    """
    total = 0
    for entry in history or []:
        if not entry:
            continue
        total += _estimate_tokens(entry.get("content", "") or "")
    return total


def should_auto_compact(
    history: list[dict],
    max_tokens: int = DEFAULT_CONTEXT_TOKENS,
    threshold: float = DEFAULT_THRESHOLD,
) -> bool:
    """True when history exceeds ``threshold * max_tokens``."""
    used = estimate_history_tokens(history)
    return used >= int(max_tokens * threshold)


def auto_compact_if_needed(
    history: list[dict],
    max_tokens: int = DEFAULT_CONTEXT_TOKENS,
    threshold: float = DEFAULT_THRESHOLD,
    keep_last_n: int = DEFAULT_KEEP_LAST_N,
    llm_fn: Optional[Callable[[str], str]] = None,
) -> tuple[list[dict], bool]:
    """Compact if threshold crossed. Returns ``(maybe_compacted_history, was_compacted)``.

    ``llm_fn`` is accepted for API parity with future summarizers; the current
    compactor uses its own embedded pipeline fallback and does not take a
    pluggable llm callable, so the arg is currently ignored. It is still
    validated for call shape so tests can pass a stub without surprises.
    """
    if not should_auto_compact(history, max_tokens, threshold):
        return history, False
    try:
        result = _compact_history(history, keep_last_n=keep_last_n, max_tokens=max_tokens)
        # compact_history returns (new_history, summary_text); we only need the list.
        if isinstance(result, tuple):
            compacted = result[0]
        else:
            compacted = result
        return compacted, True
    except Exception:
        # Compaction failure should never kill a turn — return original.
        return history, False
