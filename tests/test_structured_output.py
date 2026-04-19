"""Tests for structured output module.

No model weights required — tests use mock pipelines.
"""
import sys
sys.path.insert(0, "src")


def test_module_importable():
    from agent import structured_output
    assert hasattr(structured_output, "generate_structured")
    assert hasattr(structured_output, "_regex_extract_tool_calls")
    assert hasattr(structured_output, "is_structured_output_available")
    assert hasattr(structured_output, "TOOL_CALL_SCHEMA")


def test_regex_extract_bare_json():
    from agent.structured_output import _regex_extract_tool_calls
    text = '{"name": "read", "arguments": {"path": "/tmp/file.txt"}}'
    calls = _regex_extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "read"
    assert calls[0]["arguments"]["path"] == "/tmp/file.txt"


def test_regex_extract_code_block():
    from agent.structured_output import _regex_extract_tool_calls
    text = '```json\n{"name": "bash", "arguments": {"command": "ls"}}\n```'
    calls = _regex_extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "bash"


def test_regex_extract_no_match():
    from agent.structured_output import _regex_extract_tool_calls
    calls = _regex_extract_tool_calls("No tool calls here, just prose.")
    assert calls == []


def test_regex_extract_multiple():
    from agent.structured_output import _regex_extract_tool_calls
    text = '{"name": "read", "arguments": {}} then {"name": "grep", "arguments": {}}'
    calls = _regex_extract_tool_calls(text)
    assert len(calls) == 2
    names = [c["name"] for c in calls]
    assert "read" in names
    assert "grep" in names


def test_generate_structured_regex_fallback():
    """generate_structured with use_grammar=False uses regex on mock pipeline."""
    from agent.structured_output import generate_structured

    class MockPipeline:
        def next(self, prompt):
            yield '{"name": "read", "arguments": {"path": "foo.py"}}'

    calls = generate_structured(MockPipeline(), "prompt", max_new_tokens=32, use_grammar=False)
    assert len(calls) == 1
    assert calls[0]["name"] == "read"


def test_generate_structured_grammar_fallback():
    """With use_grammar=True on a pipeline that doesn't support grammar, falls back to regex."""
    from agent.structured_output import generate_structured

    class MockPipelineNoGrammar:
        def next(self, prompt):
            yield '{"name": "grep", "arguments": {"pattern": "foo"}}'

    calls = generate_structured(MockPipelineNoGrammar(), "prompt", max_new_tokens=32, use_grammar=True)
    assert len(calls) == 1
    assert calls[0]["name"] == "grep"


def test_tool_call_schema_valid():
    """TOOL_CALL_SCHEMA must be a valid JSON Schema object."""
    import json
    from agent.structured_output import TOOL_CALL_SCHEMA
    assert isinstance(TOOL_CALL_SCHEMA, dict)
    assert TOOL_CALL_SCHEMA.get("type") == "object"
    assert "name" in TOOL_CALL_SCHEMA.get("properties", {})


def test_cli_args_has_structured_output_flag():
    """CliArgs must have enable_structured_output bool field."""
    import sys; sys.path.insert(0, "src")
    import importlib.util, inspect
    spec = importlib.util.spec_from_file_location("args_check", "src/cli/args.mojo")
    # Can't import Mojo directly; check source file contains the field
    with open("src/cli/args.mojo") as f:
        src = f.read()
    assert "enable_structured_output" in src
    assert "Bool" in src
