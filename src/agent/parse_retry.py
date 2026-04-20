"""Tool-call parse-retry loop.

If the model emits JSON-shaped output that extract_tool_calls can't parse,
re-prompt up to `max_retries` times with an explicit format reminder.
"""
from __future__ import annotations
import re
from typing import Callable

# Heuristic: response looks like it TRIED to emit tool_call JSON
_JSON_HINT = re.compile(r'\{[^{}]*"name"\s*:')

RETRY_PROMPT = (
    "\n\nYour previous response contained what looked like a tool call but was "
    "not in the correct format. Please emit tool calls EXACTLY as:\n"
    "<tool_call>{\"name\": \"tool_name\", \"arguments\": {...}}</tool_call>\n\n"
    "Try again."
)


def looks_like_tool_call_attempt(text: str, tool_call_count: int) -> bool:
    """Return True if the model seems to have tried a tool call but failed to format.

    Conditions:
      - 0 tool calls were successfully extracted
      - response body contains `{"name":` JSON-like fragments
    """
    if tool_call_count > 0:
        return False
    if not text:
        return False
    return bool(_JSON_HINT.search(text))


def retry_parse_tool_calls(
    original_prompt: str,
    original_response: str,
    regenerate_fn: Callable[[str], str],
    extract_fn: Callable[[str], list],
    max_retries: int = 3,
) -> tuple[str, list]:
    """Re-prompt until extract_fn returns a non-empty list, up to max_retries.

    Args:
        original_prompt: the ChatML prompt that was sent
        original_response: the model's first response (already failed to parse)
        regenerate_fn(prompt) -> str: callable that runs the model
        extract_fn(text) -> list: callable that extracts tool calls

    Returns:
        (final_response, tool_calls) — final_response is the last model output,
        tool_calls is whatever extract_fn produced on that output (possibly []).
    """
    response = original_response
    for attempt in range(max_retries):
        # Re-prompt with the format reminder appended.
        retry_prompt = original_prompt + RETRY_PROMPT
        response = regenerate_fn(retry_prompt)
        calls = extract_fn(response)
        if calls:
            return response, calls
    return response, extract_fn(response)
