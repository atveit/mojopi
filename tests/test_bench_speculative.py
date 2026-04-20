"""Tests for scripts/bench_speculative.py — scaffold + slow empirical path."""
import sys, os
sys.path.insert(0, "src")
from pathlib import Path
import importlib.util
import pytest


def _load_bench_module():
    spec = importlib.util.spec_from_file_location(
        "bench_speculative",
        str(Path(__file__).parent.parent / "scripts" / "bench_speculative.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_module_importable():
    mod = _load_bench_module()
    assert hasattr(mod, "run_benchmark")
    assert hasattr(mod, "ensure_cached")
    assert hasattr(mod, "DEFAULT_MAIN")
    assert hasattr(mod, "DEFAULT_DRAFT")


def test_default_pair_documented():
    mod = _load_bench_module()
    # 1B draft pairs with 3B main — the whole point of the script.
    assert "1B" in mod.DEFAULT_DRAFT or "1b" in mod.DEFAULT_DRAFT.lower()
    assert "3B" in mod.DEFAULT_MAIN or "3b" in mod.DEFAULT_MAIN.lower()


def test_dry_run_returns_dict():
    mod = _load_bench_module()
    result = mod.run_benchmark(
        main_repo="main/repo",
        draft_repo="draft/repo",
        dry_run=True,
    )
    assert isinstance(result, dict)
    assert result["dry_run"] is True
    assert result["main_repo"] == "main/repo"
    assert result["draft_repo"] == "draft/repo"


def test_ensure_cached_returns_bool():
    mod = _load_bench_module()
    # Fake repo that doesn't exist — ensure_cached should try mlx_lm.load,
    # catch the error, return False.
    result = mod.ensure_cached("totally-fake/nonexistent-xyz-repo-123")
    assert isinstance(result, bool)


def test_script_runs_dry_run_via_subprocess():
    """CLI dry-run exits 0."""
    import subprocess
    script = Path(__file__).parent.parent / "scripts" / "bench_speculative.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"


def test_script_json_dry_run():
    """--json --dry-run outputs valid JSON."""
    import subprocess, json as jsonm
    script = Path(__file__).parent.parent / "scripts" / "bench_speculative.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    data = jsonm.loads(result.stdout)
    assert data["dry_run"] is True


# ---------------------------------------------------------------------------
# SLOW tests — require cached 3B + 1B models. Skipped by default.
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_run_real_benchmark_if_models_cached():
    """Empirical: runs the benchmark against cached Llama-3.2-3B + 1B-draft."""
    import os
    from pathlib import Path
    HF_CACHE = Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser() / "hub"
    def _cached(repo):
        return (HF_CACHE / ("models--" + repo.replace("/", "--"))).exists()

    mod = _load_bench_module()
    if not _cached(mod.DEFAULT_MAIN) or not _cached(mod.DEFAULT_DRAFT):
        pytest.skip(
            f"models not cached: main={mod.DEFAULT_MAIN}, draft={mod.DEFAULT_DRAFT}. "
            f"Run: scripts/fetch_model.sh {mod.DEFAULT_DRAFT.split('/')[-1]}"
        )

    result = mod.run_benchmark(
        main_repo=mod.DEFAULT_MAIN,
        draft_repo=mod.DEFAULT_DRAFT,
        prompt="Hello in one sentence.",
        max_new_tokens=16,
        warmup=False,
    )
    assert "baseline" in result
    assert "speculative" in result
    assert "speedup" in result
    # Throughput must be positive
    assert result["baseline"].get("throughput_tok_s", 0) > 0
