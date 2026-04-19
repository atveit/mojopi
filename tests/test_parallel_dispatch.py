"""Tests for parallel tool dispatch module."""
import sys
sys.path.insert(0, "src")
import time


def test_module_importable():
    from agent import parallel_dispatch
    assert hasattr(parallel_dispatch, "dispatch_parallel")
    assert hasattr(parallel_dispatch, "READ_ONLY_TOOLS")
    assert hasattr(parallel_dispatch, "_is_read_only")


def test_read_only_classification():
    from agent.parallel_dispatch import _is_read_only, READ_ONLY_TOOLS
    assert _is_read_only("read")
    assert _is_read_only("grep")
    assert _is_read_only("find")
    assert _is_read_only("ls")
    assert not _is_read_only("bash")
    assert not _is_read_only("edit")
    assert not _is_read_only("write")


def test_dispatch_parallel_empty():
    from agent.parallel_dispatch import dispatch_parallel
    results = dispatch_parallel([], lambda name, args: "ok")
    assert results == []


def test_dispatch_parallel_single_read():
    from agent.parallel_dispatch import dispatch_parallel
    calls = [{"name": "read", "arguments_json": '{"path": "README.md"}'}]
    results = dispatch_parallel(calls, lambda name, args: f"result:{name}")
    assert len(results) == 1
    assert results[0].result == "result:read"
    assert results[0].success


def test_dispatch_parallel_multiple_reads():
    """Multiple read-only tools dispatched in parallel, order preserved."""
    from agent.parallel_dispatch import dispatch_parallel
    import time

    def slow_dispatch(name, args):
        time.sleep(0.05)
        return f"done:{name}"

    calls = [
        {"name": "read", "arguments_json": "{}"},
        {"name": "grep", "arguments_json": "{}"},
        {"name": "find", "arguments_json": "{}"},
    ]
    t0 = time.perf_counter()
    results = dispatch_parallel(calls, slow_dispatch)
    elapsed = time.perf_counter() - t0

    assert len(results) == 3
    # Parallel: should finish much faster than 3 × 50ms = 150ms
    assert elapsed < 0.120, f"Expected parallel execution, took {elapsed:.3f}s"
    assert results[0].result == "done:read"
    assert results[1].result == "done:grep"
    assert results[2].result == "done:find"


def test_dispatch_parallel_write_is_sequential():
    """Write tools always run after parallel reads."""
    from agent.parallel_dispatch import dispatch_parallel
    order = []

    def tracked_dispatch(name, args):
        order.append(name)
        return f"ok:{name}"

    calls = [
        {"name": "bash", "arguments_json": "{}"},
        {"name": "edit", "arguments_json": "{}"},
    ]
    results = dispatch_parallel(calls, tracked_dispatch)
    assert len(results) == 2
    assert all(r.success for r in results)


def test_dispatch_parallel_error_handling():
    """Failed dispatch produces ToolResult with error set."""
    from agent.parallel_dispatch import dispatch_parallel

    def failing_dispatch(name, args):
        raise RuntimeError(f"{name} exploded")

    calls = [{"name": "read", "arguments_json": "{}"}]
    results = dispatch_parallel(calls, failing_dispatch)
    assert len(results) == 1
    assert not results[0].success
    assert "exploded" in results[0].error


def test_dispatch_parallel_if_all_read_only_true():
    from agent.parallel_dispatch import dispatch_parallel_if_all_read_only
    calls = [{"name": "read", "arguments_json": "{}"}, {"name": "grep", "arguments_json": "{}"}]
    results = dispatch_parallel_if_all_read_only(calls, lambda n, a: f"ok:{n}")
    assert results is not None
    assert len(results) == 2


def test_dispatch_parallel_if_all_read_only_false():
    from agent.parallel_dispatch import dispatch_parallel_if_all_read_only
    calls = [{"name": "read", "arguments_json": "{}"}, {"name": "bash", "arguments_json": "{}"}]
    results = dispatch_parallel_if_all_read_only(calls, lambda n, a: f"ok:{n}")
    assert results is None
