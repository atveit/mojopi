# Event type constants (parity with extensions/types.ts)
TOOL_CALL = "tool_call"
MESSAGE_START = "message_start"
MESSAGE_END = "message_end"
BEFORE_AGENT_START = "before_agent_start"
BEFORE_COMPACT = "before_compact"
CUSTOM_EVENT = "custom_event"

ALL_EVENT_TYPES = {TOOL_CALL, MESSAGE_START, MESSAGE_END, BEFORE_AGENT_START, BEFORE_COMPACT, CUSTOM_EVENT}

from dataclasses import dataclass, field
from typing import Any

@dataclass
class EventPayload:
    event_type: str
    data: dict = field(default_factory=dict)

_handlers: dict[str, list] = {t: [] for t in ALL_EVENT_TYPES}

def on(event_type: str, handler) -> None:
    """Register handler for event_type. Silently ignores unknown event types."""
    if event_type in _handlers:
        _handlers[event_type].append(handler)

def fire_event(event_type: str, data: dict = None) -> None:
    """Fire all handlers for event_type. Exceptions are caught, never propagated."""
    payload = EventPayload(event_type=event_type, data=data or {})
    for h in _handlers.get(event_type, []):
        try:
            h(payload)
        except Exception as e:
            print(f"[events] handler for '{event_type}' raised: {e}")

def clear_event_handlers(event_type: str = None) -> None:
    """Clear handlers for one event_type, or all if None."""
    if event_type is None:
        for t in _handlers:
            _handlers[t].clear()
    elif event_type in _handlers:
        _handlers[event_type].clear()

def handler_count(event_type: str) -> int:
    return len(_handlers.get(event_type, []))
