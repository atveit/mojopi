from std.testing import assert_equal, assert_true
from std.collections import List

from agent.types import AgentTool, AgentContext, HistoryEntry, ParsedToolCall
from agent.loop import extract_tool_calls, format_history_as_chatml
from agent.tool_executor import dispatch_tool


def test_extract_tool_calls_empty() raises:
    var text = String("This is a plain response with no tool calls.")
    var calls = extract_tool_calls(text)
    assert_equal(len(calls), 0)


def test_extract_tool_calls_one() raises:
    var text = String(
        'Here is my action:\n<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>\ndone.'
    )
    var calls = extract_tool_calls(text)
    assert_equal(len(calls), 1)
    assert_equal(calls[0].name, "read")
    assert_equal(calls[0].id, "tc_0")
    # arguments_json should be valid JSON containing the path
    assert_true(len(calls[0].arguments_json) > 0)


def test_extract_tool_calls_two() raises:
    var text = String(
        '<tool_call>{"name": "read", "arguments": {"path": "/tmp/a"}}</tool_call>'
        + " then "
        + '<tool_call>{"name": "ls", "arguments": {"path": "/tmp"}}</tool_call>'
    )
    var calls = extract_tool_calls(text)
    assert_equal(len(calls), 2)
    assert_equal(calls[0].name, "read")
    assert_equal(calls[0].id, "tc_0")
    assert_equal(calls[1].name, "ls")
    assert_equal(calls[1].id, "tc_1")


def test_format_history_as_chatml() raises:
    var system_prompt = String("You are a helpful assistant.")
    var history = List[HistoryEntry]()
    history.append(HistoryEntry(String("user"), String("hello")))

    var result = format_history_as_chatml(system_prompt, history)

    assert_true(result.startswith("<|begin_of_text|>"))
    assert_true("<|start_header_id|>system<|end_header_id|>" in result)
    assert_true("You are a helpful assistant." in result)
    assert_true("<|start_header_id|>user<|end_header_id|>" in result)
    assert_true("hello" in result)
    assert_true(result.endswith("<|start_header_id|>assistant<|end_header_id|>\n"))


def test_format_history_tool_result_as_user_turn() raises:
    var system_prompt = String("sys")
    var history = List[HistoryEntry]()
    history.append(HistoryEntry(String("user"), String("run a tool")))
    history.append(HistoryEntry(String("assistant"), String("calling tool")))
    history.append(HistoryEntry(
        String("tool_result"),
        String("file contents here"),
        String("tc_0"),
        String("read"),
    ))

    var result = format_history_as_chatml(system_prompt, history)

    # Tool results should be rendered as user turns with <tool_response> wrapper
    assert_true("<tool_response>" in result)
    assert_true("file contents here" in result)
    assert_true("</tool_response>" in result)


def test_dispatch_tool_unknown() raises:
    # Unknown tool: dispatch_tool first parses JSON (needs valid JSON),
    # then falls through to the else branch returning an error string.
    var result = dispatch_tool(String("nonexistent_tool_xyz"), String("{}"))
    assert_true(result.startswith("error: unknown tool:"))
    assert_true("nonexistent_tool_xyz" in result)


def main() raises:
    test_extract_tool_calls_empty()
    test_extract_tool_calls_one()
    test_extract_tool_calls_two()
    test_format_history_as_chatml()
    test_format_history_tool_result_as_user_turn()
    test_dispatch_tool_unknown()
    print("All agent loop tests passed!")
