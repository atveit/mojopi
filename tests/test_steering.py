import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import time

def test_push_and_poll():
    from agent.steering import push_steering, poll_steering, clear_steering
    clear_steering()
    push_steering("hello")
    result = poll_steering()
    assert result == "hello"

def test_poll_empty_returns_none():
    from agent.steering import poll_steering, clear_steering
    clear_steering()
    assert poll_steering() is None

def test_poll_all_drains_queue():
    from agent.steering import push_steering, poll_all_steering, clear_steering
    clear_steering()
    push_steering("a")
    push_steering("b")
    push_steering("c")
    msgs = poll_all_steering()
    assert msgs == ["a", "b", "c"]

def test_clear_empties_queue():
    from agent.steering import push_steering, poll_steering, clear_steering, queue_depth
    clear_steering()
    push_steering("x")
    push_steering("y")
    clear_steering()
    assert queue_depth() == 0

def test_queue_depth():
    from agent.steering import push_steering, queue_depth, clear_steering
    clear_steering()
    assert queue_depth() == 0
    push_steering("msg1")
    push_steering("msg2")
    assert queue_depth() == 2

def test_file_watcher(tmp_path):
    from agent.steering import start_file_watcher, poll_steering, clear_steering
    clear_steering()
    watch_file = tmp_path / "steering.txt"
    watch_file.write_text("", encoding="utf-8")
    start_file_watcher(str(watch_file), poll_interval=0.05)
    # Append a line to the file
    with open(str(watch_file), "a", encoding="utf-8") as f:
        f.write("stop now\n")
    # Wait briefly for the watcher to pick it up
    time.sleep(0.2)
    msg = poll_steering()
    assert msg == "stop now"

def test_thread_safety():
    """Push from multiple threads; all messages arrive."""
    import threading
    from agent.steering import push_steering, poll_all_steering, clear_steering
    clear_steering()
    threads = [threading.Thread(target=push_steering, args=(f"msg{i}",)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    msgs = poll_all_steering()
    assert len(msgs) == 20
