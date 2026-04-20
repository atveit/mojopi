"""Tests for agent/parallel_loop.py — automatic parallel dispatch."""
import sys
sys.path.insert(0, "src")
import time


def _calls(*pairs):
    return [{"name": n, "arguments_json": a} for n, a in pairs]


def test_module_importable():
    from agent import parallel_loop
    assert hasattr(parallel_loop, "maybe_parallel_dispatch")
    assert hasattr(parallel_loop, "all_read_only")


def test_all_read_only_empty_is_true():
    from agent.parallel_loop import all_read_only
    assert all_read_only([]) is True


def test_all_read_only_true():
    from agent.parallel_loop import all_read_only
    calls = _calls(("read", "{}"), ("grep", "{}"), ("ls", "{}"), ("find", "{}"))
    assert all_read_only(calls) is True


def test_all_read_only_false_bash():
    from agent.parallel_loop import all_read_only
    calls = _calls(("read", "{}"), ("bash", "{}"))
    assert all_read_only(calls) is False


def test_empty_batch_returns_empty():
    from agent.parallel_loop import maybe_parallel_dispatch
    results = maybe_parallel_dispatch([], lambda n, a: "ok")
    assert results == []


def test_sequential_single_call():
    """Single call — sequential path even when read-only."""
    from agent.parallel_loop import maybe_parallel_dispatch
    calls = _calls(("read", '{"path": "x"}'))
    results = maybe_parallel_dispatch(calls, lambda n, a: f"r-{n}")
    assert len(results) == 1
    assert results[0].result == "r-read"


def test_multi_read_only_goes_parallel():
    """3 read-only tools — should dispatch in parallel."""
    from agent.parallel_loop import maybe_parallel_dispatch
    calls = _calls(("read", "{}"), ("grep", "{}"), ("find", "{}"))
    def slow(name, args):
        time.sleep(0.05)
        return f"r-{name}"
    t0 = time.perf_counter()
    results = maybe_parallel_dispatch(calls, slow)
    elapsed = time.perf_counter() - t0
    # Parallel with 3 workers: ~50ms total; sequential would be 150ms
    assert elapsed < 0.120, f"expected parallel execution, took {elapsed:.3f}s"
    assert [r.result for r in results] == ["r-read", "r-grep", "r-find"]


def test_mixed_batch_stays_sequential():
    """read + bash mixed — run sequentially."""
    from agent.parallel_loop import maybe_parallel_dispatch
    order = []
    def dispatch(name, args):
        order.append(name)
        return f"r-{name}"
    calls = _calls(("read", "{}"), ("bash", "{}"), ("ls", "{}"))
    results = maybe_parallel_dispatch(calls, dispatch)
    # All 3 ran, order preserved
    assert [r.tool_name for r in results] == ["read", "bash", "ls"]


def test_order_preserved_in_parallel():
    """Even with variable per-call delay, results come back in input order."""
    from agent.parallel_loop import maybe_parallel_dispatch
    def varied(name, args):
        delays = {"read": 0.05, "grep": 0.02, "ls": 0.08}
        time.sleep(delays.get(name, 0.01))
        return f"r-{name}"
    calls = _calls(("read", "{}"), ("grep", "{}"), ("ls", "{}"))
    results = maybe_parallel_dispatch(calls, varied)
    assert [r.tool_name for r in results] == ["read", "grep", "ls"]


def test_error_in_one_call_doesnt_kill_others():
    """Error in parallel call produces ToolResult with error set, others succeed."""
    from agent.parallel_loop import maybe_parallel_dispatch
    def spotty(name, args):
        if name == "grep":
            raise RuntimeError("grep exploded")
        return f"r-{name}"
    calls = _calls(("read", "{}"), ("grep", "{}"), ("ls", "{}"))
    results = maybe_parallel_dispatch(calls, spotty)
    assert len(results) == 3
    assert results[0].success
    assert not results[1].success
    assert "exploded" in results[1].error
    assert results[2].success


def test_benchmark_reports_speedup():
    from agent.parallel_loop import benchmark_parallel_vs_sequential
    r = benchmark_parallel_vs_sequential(n_calls=3, call_delay=0.03)
    assert "sequential_s" in r
    assert "parallel_s" in r
    assert "speedup" in r
    # With 3 calls, expect roughly 2x speedup
    assert r["speedup"] > 1.5, f"expected speedup > 1.5, got {r['speedup']}"


def test_min_batch_size_threshold():
    """min_batch_size=3 means batch of 2 goes sequential even if read-only."""
    from agent.parallel_loop import maybe_parallel_dispatch
    def slow(name, args):
        time.sleep(0.05)
        return f"r-{name}"
    calls = _calls(("read", "{}"), ("grep", "{}"))  # only 2 calls
    t0 = time.perf_counter()
    results = maybe_parallel_dispatch(calls, slow, min_batch_size=3)
    elapsed = time.perf_counter() - t0
    # Sequential: ~100ms
    assert elapsed >= 0.080
    assert [r.tool_name for r in results] == ["read", "grep"]
