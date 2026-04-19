"""Abort/cancellation state for the mojopi agent loop.

A single threading.Event is the source of truth. Any component can check
is_aborted() or call request_abort() without holding a reference to the object.
"""
import threading

_abort_event = threading.Event()


def request_abort() -> None:
    """Signal that the current operation should abort. Thread-safe."""
    _abort_event.set()


def clear_abort() -> None:
    """Clear the abort flag (e.g. at the start of a new turn)."""
    _abort_event.clear()


def is_aborted() -> bool:
    """Return True if an abort has been requested. Non-blocking. Thread-safe."""
    return _abort_event.is_set()


def wait_for_abort(timeout: float = 0.0) -> bool:
    """Block for up to `timeout` seconds; return True if abort was set."""
    return _abort_event.wait(timeout=timeout)
