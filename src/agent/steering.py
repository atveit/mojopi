"""Steering message queue for the mojopi agent loop.

Design: producer(s) run in background threads and push messages into a thread-safe
queue. The Mojo loop polls via poll_steering() at each turn boundary.
No asyncio — polling only to avoid Mojo async complexity.
"""
import queue
import threading
from typing import Optional

# Module-level steering queue — shared across all producers and the single consumer.
_steering_queue: queue.Queue[str] = queue.Queue()

# Registry of running background watcher threads (for cleanup).
_watcher_threads: list[threading.Thread] = []


def push_steering(message: str) -> None:
    """Push a steering message onto the queue. Thread-safe."""
    _steering_queue.put(message)


def poll_steering() -> Optional[str]:
    """Non-blocking poll. Returns the next steering message or None.

    The Mojo loop calls this once per turn boundary.
    """
    try:
        return _steering_queue.get_nowait()
    except queue.Empty:
        return None


def poll_all_steering() -> list[str]:
    """Drain the entire queue and return all pending messages."""
    messages = []
    while True:
        try:
            messages.append(_steering_queue.get_nowait())
        except queue.Empty:
            break
    return messages


def clear_steering() -> None:
    """Discard all pending steering messages."""
    poll_all_steering()


def queue_depth() -> int:
    """Return the current number of pending messages."""
    return _steering_queue.qsize()


def start_file_watcher(path: str, poll_interval: float = 0.5) -> threading.Thread:
    """Start a background thread that watches `path` for new lines.

    Each new line appended to the file since the last poll is pushed as a
    steering message. Uses inode/size polling (no inotify dependency).

    The thread is daemonized and runs until the process exits.
    Returns the Thread object so callers can stop it if needed.
    """
    import os
    import time

    last_size = 0

    def _watch():
        nonlocal last_size
        while True:
            try:
                if os.path.exists(path):
                    current_size = os.path.getsize(path)
                    if current_size > last_size:
                        with open(path, encoding="utf-8") as f:
                            f.seek(last_size)
                            new_content = f.read(current_size - last_size)
                        for line in new_content.splitlines():
                            if line.strip():
                                push_steering(line.strip())
                        last_size = current_size
            except OSError:
                pass
            time.sleep(poll_interval)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()
    _watcher_threads.append(t)
    return t


def start_stdin_reader() -> threading.Thread:
    """Start a background thread that reads lines from stdin and pushes them.

    Useful for interactive sessions where the user types mid-agent-turn.
    The thread is daemonized.
    """
    import sys

    def _read():
        try:
            for line in sys.stdin:
                if line.strip():
                    push_steering(line.strip())
        except (EOFError, OSError):
            pass

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    _watcher_threads.append(t)
    return t
