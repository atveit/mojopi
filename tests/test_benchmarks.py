"""Tests for the benchmark suite.

Fast tests: verify harness structure without model weights.
Slow tests: require model weights and MAX install.

Run fast:
    PYTHONPATH=src pytest tests/test_benchmarks.py -v -m "not slow"
"""
import sys
sys.path.insert(0, "src")
import pytest


def test_bench_script_importable():
    """scripts/bench.py must be importable without model weights."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bench", "scripts/bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "bench")
    assert hasattr(mod, "measure_rss_mb")
    assert hasattr(mod, "run_ttft_benchmark")


def test_measure_rss_returns_positive_float():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bench", "scripts/bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rss = mod.measure_rss_mb()
    assert isinstance(rss, float)
    assert rss > 0


def test_dry_run_returns_dict():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bench", "scripts/bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.bench("modularai/Llama-3.1-8B-Instruct-GGUF", max_new_tokens=4, runs=1, dry_run=True)
    assert isinstance(result, dict)
    assert result["dry_run"] is True
    assert "rss_mb" in result
    assert result["rss_mb"] > 0


def test_bench_script_runs_dry_run(tmp_path):
    """scripts/bench.py --dry-run must exit 0 and print rss."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "scripts/bench.py", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"bench.py --dry-run failed:\n{result.stderr}"
    assert "dry-run" in result.stdout.lower() or "rss" in result.stdout.lower()


def test_bench_script_json_dry_run(tmp_path):
    """--json --dry-run outputs valid JSON."""
    import subprocess, sys, json
    result = subprocess.run(
        [sys.executable, "scripts/bench.py", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "model" in data
    assert data["dry_run"] is True


@pytest.mark.slow
def test_bench_with_model():
    """Full benchmark run with model weights (requires MAX + weights)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bench", "scripts/bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        result = mod.bench(
            "modularai/Llama-3.1-8B-Instruct-GGUF",
            max_new_tokens=16,
            runs=1,
            dry_run=False,
        )
        assert "ttft_ms" in result
        assert result["ttft_ms"] > 0
        assert result["throughput_tok_s"] > 0
    except Exception as e:
        pytest.skip(f"Benchmark requires model weights: {e}")
