"""Tests for agent/turn_summary.py — turn-cap summarization."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _entry(role: str, content: str, tool_name: str = "") -> dict:
    return {"role": role, "content": content, "tool_call_id": "", "tool_name": tool_name}


def test_module_importable():
    from agent import turn_summary

    assert hasattr(turn_summary, "summarize_turn_cap")
    assert hasattr(turn_summary, "TURN_CAP_TEMPLATE")


def test_summary_includes_user_request():
    from agent.turn_summary import summarize_turn_cap

    history = [_entry("user", "Find all TODOs in the repo")]
    result = summarize_turn_cap(history)
    assert "TODOs" in result


def test_summary_empty_history():
    from agent.turn_summary import summarize_turn_cap

    result = summarize_turn_cap([])
    assert "no user message found" in result.lower() or "no user" in result.lower()


def test_summary_includes_tool_calls():
    from agent.turn_summary import summarize_turn_cap

    history = [
        _entry("user", "find foo"),
        _entry("tool_result", "file.txt\nfile2.txt", tool_name="find"),
        _entry("tool_result", "contents here", tool_name="read"),
    ]
    result = summarize_turn_cap(history)
    assert "find" in result
    assert "read" in result


def test_summary_includes_partial_findings():
    from agent.turn_summary import summarize_turn_cap

    history = [
        _entry("user", "analyze codebase"),
        _entry("assistant", "I found 3 main modules to review..."),
    ]
    result = summarize_turn_cap(history)
    assert "3 main modules" in result


def test_summary_truncates_long_tool_output():
    from agent.turn_summary import summarize_turn_cap

    long_output = "x" * 500
    history = [
        _entry("user", "q"),
        _entry("tool_result", long_output, tool_name="read"),
    ]
    result = summarize_turn_cap(history)
    # Should include "..." truncation marker for the tool output (80-char cap)
    assert "..." in result


def test_summary_with_llm_refinement():
    from agent.turn_summary import summarize_turn_cap

    def refining_llm(prompt: str) -> str:
        return "Refined summary: user asked for X, agent found Y."

    history = [_entry("user", "question")]
    result = summarize_turn_cap(history, llm_fn=refining_llm)
    assert "Refined summary" in result


def test_summary_with_raising_llm_falls_back():
    from agent.turn_summary import summarize_turn_cap

    def bad_llm(prompt: str) -> str:
        raise RuntimeError("llm failed")

    history = [_entry("user", "hello")]
    result = summarize_turn_cap(history, llm_fn=bad_llm)
    # Falls back to the template, which includes the user request
    assert "hello" in result


def test_summary_mentions_turn_cap_number():
    from agent.turn_summary import summarize_turn_cap

    result = summarize_turn_cap([_entry("user", "q")], max_turns=7)
    assert "7" in result
