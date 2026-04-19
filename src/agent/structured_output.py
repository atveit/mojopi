"""Structured output for tool calls — JSON-Schema grammar path.

On GPU builds with MAX support, constrains generation to valid JSON.
On CPU or if grammar support is unavailable, falls back to regex extraction.
"""
from __future__ import annotations
import json
import re
from typing import Any

# Tool call JSON schema for grammar-constrained generation.
# Matches: {"name": "...", "arguments": {...}}
TOOL_CALL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "arguments": {"type": "object"}
    },
    "required": ["name", "arguments"]
}


def _try_grammar_generate(pipeline: Any, prompt: str, schema: dict, max_new_tokens: int) -> str | None:
    """Try to generate with JSON-Schema grammar constraint.
    Returns generated text, or None if grammar generation is not supported.
    """
    # Try MAX structured output API (GPU builds).
    if hasattr(pipeline, "generate_with_schema"):
        try:
            result = pipeline.generate_with_schema(prompt, schema=schema, max_new_tokens=max_new_tokens)
            return str(result)
        except Exception:
            pass
    if hasattr(pipeline, "structured_generate"):
        try:
            result = pipeline.structured_generate(prompt, schema=json.dumps(schema), max_new_tokens=max_new_tokens)
            return str(result)
        except Exception:
            pass
    return None


def _regex_extract_tool_calls(text: str) -> list[dict]:
    """Regex fallback: extract tool call JSON objects from free-form text."""
    calls = []
    # Match ```json ... ``` blocks first
    for m in re.finditer(r"```json\s*(\{[^`]+\})\s*```", text, re.DOTALL):
        try:
            obj = json.loads(m.group(1))
            if "name" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass
    if calls:
        return calls
    # Match bare JSON objects with "name" key (allow one level of nested braces for "arguments")
    for m in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\"name\"(?:[^{}]|\{[^{}]*\})*\}", text):
        try:
            obj = json.loads(m.group(0))
            if "name" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass
    return calls


def generate_structured(
    pipeline: Any,
    prompt: str,
    max_new_tokens: int = 256,
    use_grammar: bool = False,
) -> list[dict]:
    """Generate and extract tool calls.

    If use_grammar=True (GPU path), attempt grammar-constrained generation.
    Falls back to regex extraction if grammar not supported.

    Returns list of {"name": str, "arguments": dict} dicts.
    """
    if use_grammar:
        text = _try_grammar_generate(pipeline, prompt, TOOL_CALL_SCHEMA, max_new_tokens)
        if text is not None:
            try:
                obj = json.loads(text)
                if "name" in obj:
                    return [obj]
            except json.JSONDecodeError:
                pass
            # Grammar output couldn't be parsed; fall through to regex

    # Regex path: call pipeline normally then extract
    tokens = []
    if hasattr(pipeline, "next"):
        for tok in pipeline.next(prompt):
            tokens.append(str(tok))
            if len(tokens) >= max_new_tokens:
                break
    elif hasattr(pipeline, "generate"):
        tokens = [str(pipeline.generate(prompt, max_new_tokens=max_new_tokens))]
    else:
        for tok in pipeline(prompt):
            tokens.append(str(tok))
            if len(tokens) >= max_new_tokens:
                break

    text = "".join(tokens)
    return _regex_extract_tool_calls(text)


def is_structured_output_available() -> bool:
    """Return True if the current pipeline supports grammar-constrained generation."""
    try:
        from max_brain.pipeline import get_or_create_pipeline
        p = get_or_create_pipeline.__module__
        # Check if the pipeline class exposes grammar methods
        import max_brain.pipeline as mod
        if mod._pipeline_cache:
            pipeline = next(iter(mod._pipeline_cache.values()))
            return hasattr(pipeline, "generate_with_schema") or hasattr(pipeline, "structured_generate")
    except Exception:
        pass
    return False
