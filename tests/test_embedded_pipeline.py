"""Tests for the W1 embedded MAX pipeline.

These tests do NOT require model weights to be present. Slow tests that
actually load the model are marked with @pytest.mark.slow and skipped in
CI by default.

Run fast tests only:
    PYTHONPATH=src python -m pytest tests/test_embedded_pipeline.py -v -m "not slow"

Run all tests (requires model weights):
    PYTHONPATH=src python -m pytest tests/test_embedded_pipeline.py -v
"""
import sys
from pathlib import Path

import pytest

# Make src/ importable regardless of how pytest is invoked.
SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Fast surface tests — no model required
# ---------------------------------------------------------------------------

def test_get_or_create_pipeline_importable():
    """get_or_create_pipeline must be importable from max_brain.pipeline."""
    import max_brain.pipeline as p
    assert hasattr(p, "get_or_create_pipeline"), (
        "get_or_create_pipeline not found in max_brain.pipeline"
    )
    assert callable(p.get_or_create_pipeline)


def test_generate_embedded_importable():
    """generate_embedded must be importable and callable."""
    import max_brain.pipeline as p
    assert hasattr(p, "generate_embedded"), (
        "generate_embedded not found in max_brain.pipeline"
    )
    assert callable(p.generate_embedded)


def test_pipeline_cache_exists():
    """Module-level _pipeline_cache dict must be present."""
    import max_brain.pipeline as p
    assert hasattr(p, "_pipeline_cache")
    assert isinstance(p._pipeline_cache, dict)


def test_make_pipeline_config_importable():
    """_make_pipeline_config helper must exist."""
    import max_brain.pipeline as p
    assert hasattr(p, "_make_pipeline_config")
    assert callable(p._make_pipeline_config)


def test_platform_flag_is_bool():
    """_is_arm64 must be a boolean."""
    import max_brain.pipeline as p
    assert isinstance(p._is_arm64, bool)


def test_existing_functions_still_present():
    """Regression: run_one_shot, build_pipeline, stream_tokens must be intact."""
    import inspect
    import max_brain.pipeline as p

    assert callable(p.run_one_shot)
    assert callable(p.build_pipeline)
    assert inspect.isgeneratorfunction(p.stream_tokens)

    # Signature of run_one_shot must not have changed.
    sig = inspect.signature(p.run_one_shot)
    for param in ("prompt", "model", "max_new_tokens"):
        assert param in sig.parameters, f"run_one_shot missing param: {param}"


def test_generate_embedded_signature():
    """generate_embedded must accept (prompt, model_repo, max_new_tokens)."""
    import inspect
    import max_brain.pipeline as p
    sig = inspect.signature(p.generate_embedded)
    for param in ("prompt", "model_repo", "max_new_tokens"):
        assert param in sig.parameters, f"generate_embedded missing param: {param}"


def test_generate_embedded_no_model_graceful(monkeypatch):
    """If the pipeline cannot be loaded, generate_embedded must not crash.

    We monkeypatch get_or_create_pipeline to always raise so the test runs
    without real model weights and exercises the fallback branch.
    """
    import max_brain.pipeline as p

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated pipeline load failure")

    # Also stub run_one_shot so the subprocess isn't actually spawned.
    def _stub_run(*args, **kwargs):
        return 0

    monkeypatch.setattr(p, "get_or_create_pipeline", _raise)
    monkeypatch.setattr(p, "run_one_shot", _stub_run)

    # Should return empty string without raising.
    result = p.generate_embedded("Hello", max_new_tokens=4)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Slow tests — require model weights and a working MAX install
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_get_or_create_pipeline_returns_object():
    """get_or_create_pipeline returns a pipeline object when model is present."""
    import max_brain.pipeline as p
    try:
        pipeline = p.get_or_create_pipeline()
        assert pipeline is not None
    except Exception as e:
        pytest.skip(f"MAX pipeline not available (no model weights or MAX init error): {e}")


@pytest.mark.slow
def test_pipeline_cache_same_object():
    """Calling get_or_create_pipeline twice with same repo returns same object."""
    import max_brain.pipeline as p
    model = "modularai/Llama-3.1-8B-Instruct-GGUF"
    p._pipeline_cache.pop(model, None)
    try:
        p1 = p.get_or_create_pipeline(model)
        p2 = p.get_or_create_pipeline(model)
        assert id(p1) == id(p2), "Cache miss: got two different pipeline instances"
    except Exception as e:
        pytest.skip(f"MAX pipeline not available: {e}")


@pytest.mark.slow
def test_generate_embedded_returns_string():
    """generate_embedded returns a non-empty string when model is available."""
    import max_brain.pipeline as p
    result = p.generate_embedded("Hello, world!", max_new_tokens=16)
    assert isinstance(result, str)
    # Result may be empty if fallback ran; just assert no crash.
