"""Tests for --mode json and --mode rpc output modes."""
import sys
sys.path.insert(0, "src")
import io
import json


def test_module_importable():
    from agent import output_mode
    assert hasattr(output_mode, "emit")
    assert hasattr(output_mode, "emit_token")
    assert hasattr(output_mode, "emit_answer")
    assert hasattr(output_mode, "JSON_MODE")
    assert hasattr(output_mode, "RPC_MODE")


def test_emit_noop_in_print_mode(capsys):
    from agent.output_mode import emit
    emit("token", mode="print", text="hello")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_emit_json_mode(capsys):
    from agent.output_mode import emit
    emit("token", mode="json", text="hello")
    captured = capsys.readouterr()
    event = json.loads(captured.out.strip())
    assert event["type"] == "token"
    assert event["text"] == "hello"


def test_emit_answer_json(capsys):
    from agent.output_mode import emit_answer
    emit_answer("The answer is 42.", mode="json")
    captured = capsys.readouterr()
    event = json.loads(captured.out.strip())
    assert event["type"] == "answer"
    assert event["text"] == "The answer is 42."


def test_emit_tool_call_json(capsys):
    from agent.output_mode import emit_tool_call
    emit_tool_call("read", {"path": "foo.py"}, mode="json")
    captured = capsys.readouterr()
    event = json.loads(captured.out.strip())
    assert event["type"] == "tool_call"
    assert event["name"] == "read"
    assert event["arguments"]["path"] == "foo.py"


def test_emit_error_json(capsys):
    from agent.output_mode import emit_error
    emit_error("something failed", mode="json")
    captured = capsys.readouterr()
    event = json.loads(captured.out.strip())
    assert event["type"] == "error"
    assert event["message"] == "something failed"


def test_emit_rpc_mode():
    from agent.output_mode import _write_rpc_event
    buf = io.StringIO()
    import sys
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        _write_rpc_event({"type": "answer", "text": "hi"})
    finally:
        sys.stdout = old_stdout
    output = buf.getvalue()
    assert "Content-Length:" in output
    # Parse the body after headers
    header_end = output.find("\r\n\r\n")
    body = output[header_end + 4:]
    event = json.loads(body)
    assert event["type"] == "answer"


def test_read_rpc_request():
    from agent.output_mode import read_rpc_request
    payload = '{"method": "run", "prompt": "hello"}'
    raw = f"Content-Length: {len(payload)}\r\n\r\n{payload}"
    stream = io.StringIO(raw)
    req = read_rpc_request(stream)
    assert req is not None
    assert req["method"] == "run"
    assert req["prompt"] == "hello"


def test_is_valid_mode():
    from agent.output_mode import is_valid_mode
    assert is_valid_mode("json")
    assert is_valid_mode("rpc")
    assert is_valid_mode("print")
    assert not is_valid_mode("unknown")


def test_cli_args_has_output_mode():
    with open("src/cli/args.mojo") as f:
        src = f.read()
    assert "output_mode" in src
    assert "--mode" in src
