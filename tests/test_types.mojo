from std.collections import List
from std.testing import assert_equal, assert_true

from ai.types import (
    AssistantMessage,
    ImageContent,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
)


def test_text_content() raises:
    var tc = TextContent("hello world")
    assert_equal(tc.text, "hello world")


def test_image_content() raises:
    var ic = ImageContent("AAAA", "image/png")
    assert_equal(ic.data, "AAAA")
    assert_equal(ic.mime, "image/png")


def test_thinking_content() raises:
    var th = ThinkingContent("reasoning step", False, "sig-abc")
    assert_equal(th.text, "reasoning step")
    assert_true(not th.redacted)
    assert_equal(th.signature, "sig-abc")


def test_tool_call() raises:
    var call = ToolCall("call_1", "read", "{\"path\": \"/tmp/x\"}")
    assert_equal(call.id, "call_1")
    assert_equal(call.name, "read")
    assert_equal(call.arguments, "{\"path\": \"/tmp/x\"}")


def test_usage() raises:
    var u = Usage(100, 50, 20, 10, 180)
    assert_equal(u.input_tokens, 100)
    assert_equal(u.output_tokens, 50)
    assert_equal(u.cache_read_tokens, 20)
    assert_equal(u.cache_write_tokens, 10)
    assert_equal(u.total_tokens, 180)


def test_stop_reason() raises:
    var sr = StopReason("stop")
    assert_equal(sr.value, "stop")
    var sr2 = StopReason("toolUse")
    assert_equal(sr2.value, "toolUse")


def test_user_message() raises:
    var content = List[TextContent]()
    content.append(TextContent("hi"))
    var msg = UserMessage(content, Int64(1700000000000))
    assert_equal(len(msg.content), 1)
    assert_equal(msg.content[0].text, "hi")
    assert_equal(msg.timestamp, Int64(1700000000000))


def test_assistant_message() raises:
    var content = List[TextContent]()
    content.append(TextContent("answer"))
    var usage = Usage(10, 20, 0, 0, 30)
    var stop = StopReason("stop")
    var msg = AssistantMessage(
        content, "llama-3.1-8b", usage, stop, Int64(1700000001000)
    )
    assert_equal(len(msg.content), 1)
    assert_equal(msg.content[0].text, "answer")
    assert_equal(msg.model, "llama-3.1-8b")
    assert_equal(msg.usage.total_tokens, 30)
    assert_equal(msg.stop_reason.value, "stop")
    assert_equal(msg.timestamp, Int64(1700000001000))


def test_tool_result_message() raises:
    var content = List[TextContent]()
    content.append(TextContent("file contents here"))
    var msg = ToolResultMessage(
        "call_1", "read", content, False, Int64(1700000002000)
    )
    assert_equal(msg.tool_call_id, "call_1")
    assert_equal(msg.tool_name, "read")
    assert_equal(len(msg.content), 1)
    assert_equal(msg.content[0].text, "file contents here")
    assert_true(not msg.is_error)
    assert_equal(msg.timestamp, Int64(1700000002000))


def test_user_message_multi_block_round_trip() raises:
    var content = List[TextContent]()
    content.append(TextContent("first"))
    content.append(TextContent("second"))
    content.append(TextContent("third"))
    var msg = UserMessage(content, Int64(1700000003000))
    assert_equal(len(msg.content), 3)
    assert_equal(msg.content[0].text, "first")
    assert_equal(msg.content[len(msg.content) - 1].text, "third")


# Runnable entrypoint so `mojo run tests/test_types.mojo` exercises every test.
# Any test that fails raises and propagates, causing the process to exit
# non-zero — picked up by scripts/test.sh's `set -e`.
def main() raises:
    test_text_content()
    test_image_content()
    test_thinking_content()
    test_tool_call()
    test_usage()
    test_stop_reason()
    test_user_message()
    test_assistant_message()
    test_tool_result_message()
    test_user_message_multi_block_round_trip()
    print("OK: test_types (10 tests)")
