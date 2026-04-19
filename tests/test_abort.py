import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_is_aborted_false_initially():
    from agent.abort import is_aborted, clear_abort
    clear_abort()
    assert not is_aborted()

def test_request_abort_sets_flag():
    from agent.abort import request_abort, is_aborted, clear_abort
    clear_abort()
    request_abort()
    assert is_aborted()
    clear_abort()

def test_clear_abort_resets_flag():
    from agent.abort import request_abort, is_aborted, clear_abort
    clear_abort()
    request_abort()
    clear_abort()
    assert not is_aborted()

def test_bash_tool_respects_abort():
    from agent.abort import request_abort, clear_abort
    from coding_agent.tools.bash_tool import run_bash

    # Abort BEFORE execution
    clear_abort()
    request_abort()
    result = run_bash("echo should_not_run")
    clear_abort()
    # Should return aborted result without running the command
    assert result["exit_code"] == -1
    assert "aborted" in result["stderr"].lower()

def test_bash_tool_normal_without_abort():
    from agent.abort import clear_abort
    from coding_agent.tools.bash_tool import run_bash
    clear_abort()
    result = run_bash("echo hello")
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]

def test_wait_for_abort_timeout():
    import time
    from agent.abort import wait_for_abort, clear_abort
    clear_abort()
    start = time.monotonic()
    result = wait_for_abort(timeout=0.05)
    elapsed = time.monotonic() - start
    assert not result
    assert elapsed >= 0.04  # waited at least 40ms

def test_thread_safe_abort():
    import threading
    from agent.abort import request_abort, is_aborted, clear_abort
    clear_abort()
    t = threading.Thread(target=request_abort)
    t.start(); t.join()
    assert is_aborted()
    clear_abort()
