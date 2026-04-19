# src/coding_agent/compaction/compactor.py
#
# W3 Context Compaction — token counting, compaction trigger, and history
# summarisation for long agent sessions.


def estimate_tokens(text: str) -> int:
    """Rough token estimate: len(text) // 4. Good enough for compaction trigger."""
    return len(text) // 4


def estimate_history_tokens(history: list[dict]) -> int:
    """Sum estimated tokens across all history entries (role + content)."""
    total = 0
    for entry in history:
        total += estimate_tokens(entry.get("role", ""))
        total += estimate_tokens(entry.get("content", ""))
    return total


def should_compact(history: list[dict], max_tokens: int = 8192, threshold: float = 0.75) -> bool:
    """Return True if history token estimate exceeds threshold * max_tokens."""
    return estimate_history_tokens(history) > int(max_tokens * threshold)


def compact_history(
    history: list[dict],
    model: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    keep_last_n: int = 4,
    max_tokens: int = 8192,
) -> tuple[list[dict], str]:
    """Summarize old history and return (new_history, summary_text).

    Strategy:
    1. Keep the LAST `keep_last_n` turns intact (most relevant context).
    2. Summarize everything before that using generate_embedded (W1 pipeline).
    3. Return: [CompactionSentinel(summary)] + last_n_turns, plus the summary string.

    The returned history is a Python list of HistoryEntry dicts (role/content).
    The summary string is what gets written to the session as a CompactionEntry.

    Falls back to a simple "old messages omitted" stub if inference fails.
    """
    if len(history) <= keep_last_n:
        return history, ""

    old_entries = history[:-keep_last_n]
    kept_entries = history[-keep_last_n:]

    # Format old entries as readable text for the summarizer
    old_text = "\n".join(
        f"{e.get('role', '?')}: {e.get('content', '')[:200]}"
        for e in old_entries
    )

    summarizer_prompt = (
        f"Summarize the following conversation history concisely (2-3 sentences):\n\n"
        f"{old_text}\n\nSummary:"
    )

    summary = _try_generate_summary(summarizer_prompt, model)

    # Prepend a synthetic "system" entry with the summary
    new_history = [{"role": "system", "content": f"[Compacted context: {summary}]"}] + kept_entries
    return new_history, summary


def _try_generate_summary(prompt: str, model: str) -> str:
    """Try generate_embedded; fall back to stub on any error."""
    try:
        from max_brain.pipeline import generate_embedded
        result = generate_embedded(prompt, model_repo=model, max_new_tokens=128)
        return result.strip() if result.strip() else "Previous messages summarized."
    except Exception:
        return "Previous messages summarized (inference unavailable)."


def write_compaction_entry(
    session_path: str,
    parent_id: str,
    summary: str,
    token_count: int,
) -> dict:
    """Append a CompactionEntry to the session JSONL and return it.

    Uses the session store to write the entry.
    """
    import uuid
    import time
    from coding_agent.session.store import read_session, write_session

    entry = {
        "type": "compaction",
        "id": str(uuid.uuid4()),
        "parentId": parent_id,
        "summary": summary,
        "token_count": token_count,
        "timestamp": int(time.time()),
    }

    entries = read_session(session_path)
    entries.append(entry)
    write_session(session_path, entries)
    return entry
