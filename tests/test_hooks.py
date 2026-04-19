import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_no_hooks_passthrough():
    from agent.hooks import run_before_hooks, run_after_hooks, clear_hooks
    clear_hooks()
    args = '{"path": "/tmp/x"}'
    assert run_before_hooks("read", args) == args
    assert run_after_hooks("read", args, "result") == "result"

def test_before_hook_modifies_args():
    from agent.hooks import register_before_tool_call, run_before_hooks, clear_hooks
    clear_hooks()
    def hook(tool_name, args):
        return args.replace("/tmp/x", "/tmp/y")
    register_before_tool_call(hook, "redirect_hook")
    result = run_before_hooks("read", '{"path": "/tmp/x"}')
    assert "/tmp/y" in result
    clear_hooks()

def test_after_hook_modifies_result():
    from agent.hooks import register_after_tool_call, run_after_hooks, clear_hooks
    clear_hooks()
    def hook(tool_name, args, result):
        return result + "\n[post-processed]"
    register_after_tool_call(hook, "append_hook")
    result = run_after_hooks("read", "{}", "original output")
    assert "[post-processed]" in result
    clear_hooks()

def test_hook_exception_does_not_propagate():
    from agent.hooks import register_before_tool_call, run_before_hooks, clear_hooks
    clear_hooks()
    def bad_hook(tool_name, args):
        raise ValueError("hook crashed")
    register_before_tool_call(bad_hook, "bad")
    # Should not raise — exception is caught in run_before_hooks
    result = run_before_hooks("read", '{}')
    assert result == '{}'  # unchanged because hook crashed
    clear_hooks()

def test_multiple_hooks_run_in_order():
    from agent.hooks import register_before_tool_call, run_before_hooks, clear_hooks
    clear_hooks()
    log = []
    def hook1(t, a): log.append(1); return a
    def hook2(t, a): log.append(2); return a
    register_before_tool_call(hook1)
    register_before_tool_call(hook2)
    run_before_hooks("tool", "{}")
    assert log == [1, 2]
    clear_hooks()

def test_hook_count():
    from agent.hooks import register_before_tool_call, register_after_tool_call, hook_count, clear_hooks
    clear_hooks()
    register_before_tool_call(lambda t, a: a)
    register_before_tool_call(lambda t, a: a)
    register_after_tool_call(lambda t, a, r: r)
    counts = hook_count()
    assert counts["before"] == 2
    assert counts["after"] == 1
    clear_hooks()

def test_clear_hooks():
    from agent.hooks import register_before_tool_call, clear_hooks, hook_count
    register_before_tool_call(lambda t, a: a)
    clear_hooks()
    assert hook_count()["before"] == 0
