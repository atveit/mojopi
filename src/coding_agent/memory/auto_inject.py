"""Auto-injection bridge between the memory store and the agent loop.

Two public entry points the loop (or lead wiring in main.mojo) calls:

1. augment_system_prompt(base_prompt, query, k=3) — retrieve top-k memories
   relevant to `query` and append them as a '## Relevant memories' section
   to `base_prompt`. Returns the augmented prompt (or the base prompt
   unchanged if retrieval is empty).

2. extract_after_session(session_id, transcript, llm_fn=None) — extract
   durable facts from a completed transcript and persist them to the store.
   Fire-and-forget; never raises; returns the count stored.
"""
from __future__ import annotations
from typing import Optional, Callable

from coding_agent.memory.retriever import retrieve_relevant, format_for_prompt
from coding_agent.memory.extractor import extract_from_session

AUTO_MEMORY_HEADER = "## Relevant memories from past sessions"
DEFAULT_K = 3
MIN_SCORE = 0.05  # drop near-zero matches (pure noise from BoW fallback)


def augment_system_prompt(
    base_prompt: str,
    query: str,
    k: int = DEFAULT_K,
    min_score: float = MIN_SCORE,
) -> str:
    """Append top-k relevant memories to the system prompt.

    Returns `base_prompt` unchanged if there are no memories above min_score.
    Safe to call with empty query (returns base).
    """
    if not query or not query.strip():
        return base_prompt
    try:
        results = retrieve_relevant(query, k=k)
    except Exception:
        return base_prompt
    filtered = [(e, s) for e, s in results if s >= min_score]
    if not filtered:
        return base_prompt
    header = AUTO_MEMORY_HEADER
    body = format_for_prompt(filtered)
    # format_for_prompt already prints "## Relevant memories\n..." — replace its
    # heading with our clearer auto-memory one for clarity.
    body = body.replace("## Relevant memories", header, 1)
    if base_prompt.endswith("\n"):
        sep = ""
    else:
        sep = "\n\n"
    return base_prompt + sep + body


def extract_after_session(
    session_id: str,
    transcript: str,
    llm_fn: Optional[Callable[[str], str]] = None,
) -> int:
    """Run fact extraction over a session transcript; return count stored.

    Never raises — swallows any extractor failure so closing a session never
    blocks on a memory bug. Returns 0 on failure.
    """
    if not transcript or not transcript.strip():
        return 0
    try:
        stored = extract_from_session(
            transcript=transcript,
            source=f"session:{session_id}",
            llm_fn=llm_fn,
        )
        return len(stored)
    except Exception:
        return 0


def should_inject_memory(env_var_name: str = "MOJOPI_AUTO_MEMORY") -> bool:
    """Gate auto-injection behind an env var (default: enabled).

    Allows users to disable with MOJOPI_AUTO_MEMORY=0. Returns True when
    the variable is unset, "1", "true", "yes", etc.; False when "0", "false", "no".
    """
    import os
    raw = os.environ.get(env_var_name, "1").strip().lower()
    return raw not in {"0", "false", "no", "off", ""}
