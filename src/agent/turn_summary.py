"""Turn-cap summarization: when ``MAX_TOOL_ITERATIONS`` is hit, summarize state.

Rather than returning ``'[agent: max tool iterations reached]'`` and leaving
the user in the dark, produce a human-readable summary of:
  - what the user asked
  - which tools were called and with what args (last 6)
  - what partial progress was made
  - recommended next step
"""
from __future__ import annotations

from typing import Callable, Optional

TURN_CAP_TEMPLATE = """I hit the tool-iteration cap ({max_turns} turns) before finishing the task.

Here's where I got to:

**Your request:** {user_request}

**Tools I called ({tool_count} so far):**
{tool_log}

**Partial findings:**
{findings}

**Suggested next step:** Run me again with a more specific prompt targeting the one piece you care about, or increase --max-turns."""


def _extract_user_request(history: list[dict]) -> str:
    """The first user message is the original request."""
    for entry in history or []:
        if entry.get("role") == "user":
            return (entry.get("content", "") or "").strip()[:200]
    return "(no user message found)"


def _summarize_tool_calls(history: list[dict], last_n: int = 6) -> tuple[str, int]:
    """Return (formatted_tool_log, total_count)."""
    tool_events: list[str] = []
    for entry in history or []:
        if entry.get("role") == "tool_result":
            name = entry.get("tool_name", "?") or "?"
            snippet = (entry.get("content", "") or "").strip()
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            tool_events.append(f"- **{name}**: {snippet}")
    total = len(tool_events)
    shown = tool_events[-last_n:]
    formatted = "\n".join(shown) if shown else "(no tools were called)"
    return formatted, total


def _last_assistant_text(history: list[dict]) -> str:
    """The last assistant text is the nearest partial finding."""
    for entry in reversed(history or []):
        if entry.get("role") == "assistant":
            text = (entry.get("content", "") or "").strip()
            if len(text) > 500:
                text = text[:497] + "..."
            return text or "(no assistant text)"
    return "(no partial findings)"


def summarize_turn_cap(
    history: list[dict],
    max_turns: int = 10,
    llm_fn: Optional[Callable[[str], str]] = None,
) -> str:
    """Produce a human-readable summary of turn-cap state.

    ``llm_fn`` is optional; when provided, it can refine the default template.
    Falls back to the template unconditionally if ``llm_fn`` is None or raises.
    """
    user_request = _extract_user_request(history)
    tool_log, tool_count = _summarize_tool_calls(history)
    findings = _last_assistant_text(history)

    template_result = TURN_CAP_TEMPLATE.format(
        max_turns=max_turns,
        user_request=user_request,
        tool_count=tool_count,
        tool_log=tool_log,
        findings=findings,
    )

    if llm_fn is None:
        return template_result

    try:
        refine_prompt = (
            "Rewrite the following turn-cap summary into a tight, user-friendly paragraph. "
            "Keep the structure but make it natural.\n\n" + template_result
        )
        refined = llm_fn(refine_prompt).strip()
        return refined if refined else template_result
    except Exception:
        return template_result
