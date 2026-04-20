"""Extract durable facts from a completed session via the LLM."""
from __future__ import annotations
import json
import re
from typing import Optional, Callable

from coding_agent.memory.store import store_memory, TYPE_PROJECT_FACT, VALID_TYPES
from coding_agent.memory.embeddings import embed_text

EXTRACTION_PROMPT = """Given the following session transcript, extract up to 5 durable facts that would be useful for future sessions with this user.

A durable fact:
- is specific and non-obvious
- reflects a user preference, project constraint, technical decision, or tool observation
- is NOT a one-off question or ephemeral detail

Return JSON ONLY, no prose. Array of objects:
[
  {{"text": "...", "type": "user_preference|project_fact|tool_observation|decision", "confidence": 0.0-1.0}}
]

Transcript:
{transcript}

JSON:"""


def extract_from_session(
    transcript: str,
    source: str = "",
    llm_fn: Optional[Callable[[str], str]] = None,
) -> list[dict]:
    """Extract and store memories from a transcript.

    llm_fn(prompt) -> str should return JSON; defaults to `generate_embedded`.
    Returns list of entry dicts (also persisted via store_memory).
    """
    prompt = EXTRACTION_PROMPT.format(transcript=transcript[:8000])

    if llm_fn is None:
        try:
            from max_brain.pipeline import generate_embedded
            llm_fn = lambda p: generate_embedded(p, max_new_tokens=512)
        except Exception:
            return []

    raw = llm_fn(prompt)
    parsed = _parse_extraction_output(raw)

    stored = []
    for fact in parsed:
        text = fact.get("text", "").strip()
        if not text:
            continue
        ftype = fact.get("type", TYPE_PROJECT_FACT)
        if ftype not in VALID_TYPES:
            ftype = TYPE_PROJECT_FACT
        conf = float(fact.get("confidence", 0.75))
        vec = embed_text(text)
        entry = store_memory(text=text, embedding=vec, source=source, type=ftype, confidence=conf)
        stored.append(entry.to_dict())
    return stored


def _parse_extraction_output(raw: str) -> list[dict]:
    """Extract the first JSON array from LLM output; tolerate prose before/after."""
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        return []
    try:
        parsed = json.loads(m.group(0))
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    return []
