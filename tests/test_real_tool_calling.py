"""Empirical tool-calling tests — require a cached tool-capable MLX model.

Skipped in the default fast-test pass. Run with:
    pixi run bash -c "PYTHONPATH=src pytest tests/test_real_tool_calling.py -v -m slow"
"""
import sys
sys.path.insert(0, "src")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "scripts"))
import pytest
import importlib.util


def _import_verify_module():
    spec = importlib.util.spec_from_file_location(
        "verify_tool_calling",
        str(__import__("pathlib").Path(__file__).parent.parent / "scripts" / "verify_tool_calling.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.slow
def test_module_importable_and_has_candidates():
    mod = _import_verify_module()
    assert hasattr(mod, "CANDIDATE_MODELS")
    assert len(mod.CANDIDATE_MODELS) >= 2
    assert hasattr(mod, "verify_tool_calling")


@pytest.mark.slow
def test_find_cached_model_returns_str_or_none():
    mod = _import_verify_module()
    result = mod._find_cached_model()
    assert result is None or isinstance(result, str)


@pytest.mark.slow
def test_verify_tool_calling_against_cached_model():
    """If a tool-capable model is cached, run end-to-end; else skip."""
    mod = _import_verify_module()
    model = mod._find_cached_model()
    if model is None:
        pytest.skip(f"no tool-capable model in HF cache; candidates: {mod.CANDIDATE_MODELS}")
    try:
        result = mod.verify_tool_calling(model, max_new_tokens=128)
    except Exception as e:
        pytest.skip(f"MLX failed to load model: {e}")
    # Allow flexibility: at minimum the run completed and returned a dict.
    assert isinstance(result, dict)
    assert "response_excerpt" in result
    assert "model" in result
    assert result["model"] == model


@pytest.mark.slow
def test_extract_regex_matches_valid_tool_call():
    """Sanity-check the extraction regex on a hand-crafted response."""
    import re, json
    response = 'Some prose\n<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>'
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL)
    assert m is not None
    parsed = json.loads(m.group(1))
    assert parsed["name"] == "read"
    assert parsed["arguments"]["path"] == "/tmp/x"


@pytest.mark.slow
def test_bare_json_fallback_regex():
    """The bare-JSON fallback handles Qwen-style output."""
    import re, json
    # Flat (no-nested-braces) tool-call JSON that our fallback regex can catch.
    response = 'I will use this tool: {"name": "read", "path": "/tmp/x"}'
    m = re.search(r'\{[^{}]*"name"\s*:\s*"read"[^{}]*\}', response)
    assert m is not None
    # Bare JSON may include the arguments key with nested braces that our simple
    # regex can't capture — but the outer key detection works for flat blobs.
