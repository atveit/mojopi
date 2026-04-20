"""Top-k cosine-similarity retrieval over the memory store."""
from __future__ import annotations
from typing import Optional

from coding_agent.memory.store import list_memories, MemoryEntry
from coding_agent.memory.embeddings import embed_text, cosine_similarity


def retrieve_relevant(
    query: str,
    k: int = 5,
    type: Optional[str] = None,
    min_confidence: float = 0.0,
) -> list[tuple[MemoryEntry, float]]:
    """Return up to k (entry, score) pairs most similar to query.

    If fewer than k entries exist, returns fewer. Entries below min_confidence
    are excluded.
    """
    memories = list_memories(type=type)
    if not memories:
        return []
    q_vec = embed_text(query)
    scored = []
    for m in memories:
        if m.confidence < min_confidence:
            continue
        if not m.embedding:
            continue
        s = cosine_similarity(q_vec, m.embedding)
        scored.append((m, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def format_for_prompt(results: list[tuple[MemoryEntry, float]]) -> str:
    """Render retrieved memories as a system-prompt-ready string."""
    if not results:
        return ""
    lines = ["## Relevant memories\n"]
    for entry, score in results:
        lines.append(f"- [{entry.type}, conf={entry.confidence:.2f}] {entry.text}")
    return "\n".join(lines)
