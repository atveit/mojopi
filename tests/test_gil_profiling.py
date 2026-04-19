"""Tests for GIL profiling and threaded pipeline infrastructure.

No model weights required — tests verify the infrastructure without running inference.
"""
import sys
sys.path.insert(0, "src")
import time


def test_threaded_pipeline_importable():
    from max_brain import threaded_pipeline
    assert hasattr(threaded_pipeline, "MaxInferencePool")
    assert hasattr(threaded_pipeline, "generate_threaded")
    assert hasattr(threaded_pipeline, "get_inference_pool")


def test_inference_pool_starts():
    from max_brain.threaded_pipeline import MaxInferencePool
    pool = MaxInferencePool()
    assert pool._thread.is_alive()
    pool.shutdown()


def test_inference_pool_metrics_initial():
    from max_brain.threaded_pipeline import MaxInferencePool
    pool = MaxInferencePool()
    metrics = pool.get_metrics()
    assert metrics["calls"] == 0
    assert metrics["total_tokens"] == 0
    pool.shutdown()


def test_singleton_pool():
    from max_brain.threaded_pipeline import get_inference_pool
    p1 = get_inference_pool()
    p2 = get_inference_pool()
    assert p1 is p2


def test_gil_profiler_importable():
    from max_brain import gil_profiler
    assert hasattr(gil_profiler, "profile_gil")
    assert hasattr(gil_profiler, "GilProfile")
    assert hasattr(gil_profiler, "report_metrics")


def test_profile_gil_context_manager():
    from max_brain.gil_profiler import profile_gil, report_metrics
    with profile_gil("test_block") as prof:
        time.sleep(0.05)
    assert prof.wall_time_ms >= 40  # at least 40ms for 50ms sleep (with some tolerance)
    metrics = report_metrics(prof)
    assert "wall_time_ms" in metrics
    assert metrics["wall_time_ms"] >= 40


def test_gil_profile_fraction_in_range():
    from max_brain.gil_profiler import profile_gil
    with profile_gil() as prof:
        x = sum(range(100_000))  # CPU-bound Python
    assert 0.0 <= prof.gil_fraction <= 1.0


def test_report_metrics_structure():
    from max_brain.gil_profiler import GilProfile, report_metrics
    prof = GilProfile(wall_time_ms=100.0, estimated_gil_hold_ms=60.0, sample_count=10)
    m = report_metrics(prof)
    assert m["wall_time_ms"] == 100.0
    assert m["estimated_gil_hold_ms"] == 60.0
    assert abs(m["gil_fraction"] - 0.6) < 0.01
    assert m["sample_count"] == 10


def test_inference_task_timeout():
    """_InferenceTask.wait() raises TimeoutError if event never set."""
    from max_brain.threaded_pipeline import _InferenceTask
    task = _InferenceTask("prompt", "model", 4)
    raised = False
    try:
        task.wait(timeout=0.01)
    except TimeoutError:
        raised = True
    assert raised
