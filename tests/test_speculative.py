"""Tests for max_brain/speculative.py - speculative decoding via MLX draft model.

No model weights required - tests mock mlx_lm.load and stream_generate.
"""
import sys
sys.path.insert(0, "src")
import pytest


def test_module_importable():
    from max_brain import speculative
    assert hasattr(speculative, "generate_speculative")
    assert hasattr(speculative, "stream_speculative")
    assert hasattr(speculative, "benchmark_speculative")
    assert hasattr(speculative, "DEFAULT_MAIN")
    assert hasattr(speculative, "DEFAULT_DRAFT")


def test_is_available_returns_bool():
    from max_brain.speculative import is_available
    assert isinstance(is_available(), bool)


def test_clear_cache():
    from max_brain.speculative import clear_cache, _spec_cache
    _spec_cache["dummy"] = "test"
    clear_cache()
    assert len(_spec_cache) == 0


def test_generate_fallback_when_draft_fails(monkeypatch):
    """When draft model fails to load, falls back to main-only generate."""
    from max_brain import speculative
    speculative.clear_cache()

    # Mock mlx_lm.load: main loads, draft raises
    class FakeModel:
        pass

    call_count = [0]

    def fake_load(repo):
        call_count[0] += 1
        if "Llama-3.2" in repo or "1B" in repo or repo == "draft-y":
            raise RuntimeError("draft not found")
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    # Mock generate
    def fake_generate(model, tokenizer, prompt, **kwargs):
        # Verify draft_model was NOT passed (because it failed)
        assert "draft_model" not in kwargs
        return "fallback output"

    monkeypatch.setattr(mlx_lm, "generate", fake_generate)

    result = speculative.generate_speculative("test", main_repo="main-x", draft_repo="draft-y")
    assert result == "fallback output"
    speculative.clear_cache()


def test_generate_uses_draft_when_available(monkeypatch):
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    def fake_load(repo):
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    captured_kwargs = {}

    def fake_generate(model, tokenizer, prompt, **kwargs):
        captured_kwargs.update(kwargs)
        return "speculative output"

    monkeypatch.setattr(mlx_lm, "generate", fake_generate)

    result = speculative.generate_speculative("test", main_repo="main-x", draft_repo="draft-y")
    assert result == "speculative output"
    assert "draft_model" in captured_kwargs
    speculative.clear_cache()


def test_stream_speculative_yields(monkeypatch):
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    def fake_load(repo):
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    class FakeResp:
        def __init__(self, text):
            self.text = text

    def fake_stream(model, tokenizer, prompt, **kwargs):
        for t in ["a", "b", "c"]:
            yield FakeResp(t)

    monkeypatch.setattr(mlx_lm, "stream_generate", fake_stream)

    out = list(speculative.stream_speculative("test", main_repo="main-x", draft_repo="draft-y"))
    assert out == ["a", "b", "c"]
    speculative.clear_cache()


def test_benchmark_returns_structured_dict(monkeypatch):
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    def fake_load(repo):
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    class FakeResp:
        def __init__(self, text):
            self.text = text

    def fake_stream(model, tokenizer, prompt, **kwargs):
        # Emit 5 tokens
        for i in range(5):
            yield FakeResp(f"t{i}")

    monkeypatch.setattr(mlx_lm, "stream_generate", fake_stream)

    result = speculative.benchmark_speculative(prompt="q", main_repo="main-x", draft_repo="draft-y", max_new_tokens=5)
    assert "baseline" in result
    assert "speculative" in result
    assert "speedup" in result
    assert result["baseline"]["total_tokens"] == 5
    assert result["speculative"]["total_tokens"] == 5
    assert isinstance(result["speedup"], float)
    speculative.clear_cache()


def test_benchmark_notes_when_draft_unavailable(monkeypatch):
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    def fake_load(repo):
        if "1B" in repo or "Llama-3.2" in repo or repo == "draft-y":
            raise RuntimeError("no draft")
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    class FakeResp:
        def __init__(self, text):
            self.text = text

    def fake_stream(model, tokenizer, prompt, **kwargs):
        for i in range(3):
            yield FakeResp(f"t{i}")

    monkeypatch.setattr(mlx_lm, "stream_generate", fake_stream)

    result = speculative.benchmark_speculative(main_repo="main-x", draft_repo="draft-y", max_new_tokens=3)
    assert result["draft_model"] is None
    assert result["speedup"] == 1.0
    assert "note" in result
    speculative.clear_cache()


def test_load_pair_cached(monkeypatch):
    """_load_pair should cache per (main, draft) tuple and not re-load."""
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    call_counter = {"n": 0}

    def fake_load(repo):
        call_counter["n"] += 1
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    # First call: loads both main + draft -> 2 calls
    t1 = speculative._load_pair("main-a", "draft-a")
    n_after_first = call_counter["n"]
    assert n_after_first == 2

    # Second call with same key: cached, no new load
    t2 = speculative._load_pair("main-a", "draft-a")
    assert call_counter["n"] == n_after_first
    assert t1 is t2

    # Different key: triggers fresh load
    speculative._load_pair("main-b", "draft-b")
    assert call_counter["n"] == n_after_first + 2

    speculative.clear_cache()


def test_defaults_point_at_expected_repos():
    """Sanity check on default model choices."""
    from max_brain import speculative
    assert "Llama" in speculative.DEFAULT_MAIN
    assert "1B" in speculative.DEFAULT_DRAFT or "Llama-3.2" in speculative.DEFAULT_DRAFT


def test_run_stream_metrics_shape():
    """_run_stream should return all four required metric keys."""
    from max_brain.speculative import _run_stream

    def gen():
        for t in ["x", "y", "z", "w"]:
            yield t

    metrics = _run_stream(gen, prompt="ignored", max_new_tokens=10)
    assert set(metrics.keys()) == {"ttft_ms", "throughput_tok_s", "total_tokens", "total_time_s"}
    assert metrics["total_tokens"] == 4
    assert metrics["total_time_s"] >= 0
    assert metrics["ttft_ms"] >= 0


def test_stream_speculative_without_draft(monkeypatch):
    """If draft fails, stream_speculative should still yield via main-only path."""
    from max_brain import speculative
    speculative.clear_cache()

    class FakeModel:
        pass

    def fake_load(repo):
        if repo == "draft-y":
            raise RuntimeError("no draft")
        return (FakeModel(), "tok")

    import mlx_lm
    monkeypatch.setattr(mlx_lm, "load", fake_load)

    class FakeResp:
        def __init__(self, text):
            self.text = text

    captured = {}

    def fake_stream(model, tokenizer, prompt, **kwargs):
        captured.update(kwargs)
        for t in ["hello", " ", "world"]:
            yield FakeResp(t)

    monkeypatch.setattr(mlx_lm, "stream_generate", fake_stream)

    out = list(speculative.stream_speculative("test", main_repo="main-x", draft_repo="draft-y"))
    assert out == ["hello", " ", "world"]
    # With no draft model, kwargs should lack draft_model
    assert "draft_model" not in captured
    speculative.clear_cache()
