"""Tests for agent/thinking.py — thinking-token stripping."""
import sys
sys.path.insert(0, "src")


def test_module_importable():
    from agent import thinking
    assert hasattr(thinking, "strip_thinking")
    assert hasattr(thinking, "strip_thinking_text")
    assert hasattr(thinking, "has_thinking_block")


def test_empty_text():
    from agent.thinking import strip_thinking
    r = strip_thinking("")
    assert r.visible == ""
    assert r.thinking == ""


def test_no_thinking_tag():
    from agent.thinking import strip_thinking
    r = strip_thinking("Just a plain response.")
    assert r.visible == "Just a plain response."
    assert r.thinking == ""
    assert not r.has_thinking()


def test_strip_think_tag():
    from agent.thinking import strip_thinking
    text = "<think>Let me reason</think>The answer is 4."
    r = strip_thinking(text)
    assert "Let me reason" not in r.visible
    assert r.visible == "The answer is 4."
    assert r.thinking == "Let me reason"


def test_strip_thinking_tag():
    from agent.thinking import strip_thinking
    text = "<thinking>Hmm</thinking>Response"
    r = strip_thinking(text)
    assert r.visible == "Response"
    assert r.thinking == "Hmm"


def test_strip_multiline_think():
    from agent.thinking import strip_thinking
    text = "<think>\nLine 1\nLine 2\n</think>\n\nVisible content."
    r = strip_thinking(text)
    assert r.visible == "Visible content."
    assert "Line 1" in r.thinking
    assert "Line 2" in r.thinking


def test_strip_multiple_blocks():
    from agent.thinking import strip_thinking
    text = "<think>first</think>A<think>second</think>B"
    r = strip_thinking(text)
    assert "first" not in r.visible
    assert "second" not in r.visible
    assert r.visible == "AB"
    assert "first" in r.thinking
    assert "second" in r.thinking


def test_unclosed_think_truncates_to_end():
    from agent.thinking import strip_thinking
    text = "Before<think>unfinished reasoning that never closes"
    r = strip_thinking(text)
    assert r.visible == "Before"
    assert "unfinished reasoning" in r.thinking


def test_pipe_style_thinking():
    from agent.thinking import strip_thinking
    text = "<|thinking|>reasoning<|/thinking|>answer"
    r = strip_thinking(text)
    assert r.visible == "answer"
    assert r.thinking == "reasoning"


def test_codefence_thinking():
    from agent.thinking import strip_thinking
    text = "```thinking\nanalysis\n```\nResult: 42"
    r = strip_thinking(text)
    assert "analysis" not in r.visible
    assert "Result: 42" in r.visible


def test_strip_thinking_text_convenience():
    from agent.thinking import strip_thinking_text
    assert strip_thinking_text("<think>x</think>visible") == "visible"


def test_has_thinking_block():
    from agent.thinking import has_thinking_block
    assert has_thinking_block("<think>x</think>")
    assert has_thinking_block("<thinking>y</thinking>")
    assert not has_thinking_block("plain text")
    assert not has_thinking_block("")


def test_case_insensitive():
    from agent.thinking import strip_thinking
    text = "<Think>upper</Think>visible"
    r = strip_thinking(text)
    assert r.visible == "visible"


def test_preserves_tool_call_tags():
    """<tool_call> must NOT be stripped by thinking remover."""
    from agent.thinking import strip_thinking
    text = '<think>planning</think><tool_call>{"name":"read"}</tool_call>'
    r = strip_thinking(text)
    assert "<tool_call>" in r.visible
    assert "planning" in r.thinking
