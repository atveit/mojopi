"""JSONL output modes for mojopi.

json mode: each event is a newline-delimited JSON object to stdout
rpc mode: same events but framed for RPC (Content-Length header + JSON body)

Event types:
  {"type": "token", "text": "..."}
  {"type": "tool_call", "name": "...", "arguments": {...}}
  {"type": "tool_result", "name": "...", "result": "..."}
  {"type": "answer", "text": "..."}
  {"type": "error", "message": "..."}
  {"type": "ping"}                    (rpc mode keepalive)
"""
import json
import sys
from typing import Any

# Output mode constants
JSON_MODE = "json"
RPC_MODE = "rpc"
PRINT_MODE = "print"


def _write_json_event(event: dict) -> None:
    """Write a single JSON event to stdout (json mode)."""
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def _write_rpc_event(event: dict) -> None:
    """Write a JSONL-framed RPC event (Content-Length header + body)."""
    body = json.dumps(event)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    sys.stdout.write(header + body)
    sys.stdout.flush()


def emit(event_type: str, mode: str = PRINT_MODE, **kwargs: Any) -> None:
    """Emit a structured event. No-op in print mode.

    Args:
        event_type: "token", "tool_call", "tool_result", "answer", "error", "ping"
        mode: "json", "rpc", or "print" (no-op for print)
        **kwargs: event payload fields
    """
    if mode == PRINT_MODE:
        return
    event = {"type": event_type, **kwargs}
    if mode == JSON_MODE:
        _write_json_event(event)
    elif mode == RPC_MODE:
        _write_rpc_event(event)


def emit_token(text: str, mode: str = PRINT_MODE) -> None:
    emit("token", mode=mode, text=text)


def emit_tool_call(name: str, arguments: dict, mode: str = PRINT_MODE) -> None:
    emit("tool_call", mode=mode, name=name, arguments=arguments)


def emit_tool_result(name: str, result: str, mode: str = PRINT_MODE) -> None:
    emit("tool_result", mode=mode, name=name, result=result)


def emit_answer(text: str, mode: str = PRINT_MODE) -> None:
    emit("answer", mode=mode, text=text)


def emit_error(message: str, mode: str = PRINT_MODE) -> None:
    emit("error", mode=mode, message=message)


def read_rpc_request(stream=None) -> dict | None:
    """Read one RPC request from stream (default: stdin).

    Format: Content-Length: <n>\r\n\r\n<json>
    Returns parsed dict or None on EOF/error.
    """
    s = stream or sys.stdin
    try:
        header = ""
        while True:
            line = s.readline()
            if not line:
                return None
            line = line.rstrip("\r\n")
            if not line:
                break
            header += line + "\n"

        content_length = None
        for h in header.splitlines():
            if h.lower().startswith("content-length:"):
                content_length = int(h.split(":", 1)[1].strip())

        if content_length is None:
            return None

        body = s.read(content_length)
        return json.loads(body)
    except Exception:
        return None


def is_valid_mode(mode: str) -> bool:
    return mode in {JSON_MODE, RPC_MODE, PRINT_MODE}
