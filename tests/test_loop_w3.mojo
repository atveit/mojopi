from std.testing import assert_equal, assert_true
from std.collections import List
from agent.loop import extract_tool_calls, format_history_as_chatml
from agent.types import HistoryEntry, AgentContext, AgentTool
from agent.steering import push_steering, clear_steering, poll_steering
from agent.abort import request_abort, clear_abort, is_aborted

def test_abort_flag_clear_on_start() raises:
    # After clear_abort, is_aborted returns False.
    request_abort()
    clear_abort()
    assert_equal(is_aborted(), False)

def test_abort_flag_request() raises:
    clear_abort()
    request_abort()
    assert_equal(is_aborted(), True)
    clear_abort()  # cleanup

def test_steering_push_poll() raises:
    clear_steering()
    push_steering(String("stop now"))
    var msg = poll_steering()
    assert_equal(msg, String("stop now"))

def test_steering_empty_returns_empty() raises:
    clear_steering()
    var msg = poll_steering()
    assert_equal(msg, String(""))

def test_extract_tool_calls_still_works() raises:
    var text = String('<tool_call>{"name": "ls", "arguments": {"path": "."}}</tool_call>')
    var calls = extract_tool_calls(text)
    assert_equal(len(calls), 1)
    assert_equal(calls[0].name, "ls")

def main() raises:
    test_abort_flag_clear_on_start()
    test_abort_flag_request()
    test_steering_push_poll()
    test_steering_empty_returns_empty()
    test_extract_tool_calls_still_works()
    print("All W3 loop integration tests passed!")
