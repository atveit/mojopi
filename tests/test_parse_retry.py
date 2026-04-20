"""Tests for agent/parse_retry.py — tool-call parse-retry loop."""
import sys
sys.path.insert(0, "src")


def test_module_importable():
    from agent import parse_retry
    assert hasattr(parse_retry, "looks_like_tool_call_attempt")
    assert hasattr(parse_retry, "retry_parse_tool_calls")


def test_looks_like_success_means_no_retry_needed():
    from agent.parse_retry import looks_like_tool_call_attempt
    # tool_call_count > 0 => no retry
    assert not looks_like_tool_call_attempt('{"name": "read"}', tool_call_count=1)


def test_looks_like_json_attempt():
    from agent.parse_retry import looks_like_tool_call_attempt
    text = 'Let me use {"name": "read", "args": {"path": "foo"}}'
    assert looks_like_tool_call_attempt(text, tool_call_count=0)


def test_looks_like_no_json_no_retry():
    from agent.parse_retry import looks_like_tool_call_attempt
    assert not looks_like_tool_call_attempt("just prose with no json", tool_call_count=0)


def test_retry_succeeds_on_second_try():
    from agent.parse_retry import retry_parse_tool_calls

    responses = iter([
        'bad json {"name"',
        '<tool_call>{"name":"read","arguments":{}}</tool_call>',
    ])

    def regen(_):
        return next(responses)

    def extract(text):
        # Simple mock: return [1] if the text has a closing </tool_call>
        if "</tool_call>" in text:
            return [{"name": "read"}]
        return []

    final, calls = retry_parse_tool_calls("orig", "initial bad", regen, extract, max_retries=3)
    assert calls == [{"name": "read"}]


def test_retry_exhausted_returns_empty():
    from agent.parse_retry import retry_parse_tool_calls

    def regen(_):
        return "still no tool call"

    def extract(text):
        return []

    final, calls = retry_parse_tool_calls("orig", "first", regen, extract, max_retries=3)
    assert calls == []


def test_retry_zero_max_retries():
    from agent.parse_retry import retry_parse_tool_calls

    regen_calls = [0]

    def regen(_):
        regen_calls[0] += 1
        return ""

    def extract(_text):
        return []

    retry_parse_tool_calls("orig", "first", regen, extract, max_retries=0)
    assert regen_calls[0] == 0
