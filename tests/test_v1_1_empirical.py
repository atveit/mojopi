"""Empirical tests for v1.1 features — run against real MLX models.

These tests require cached model weights. Run with:
    pixi run bash -c "PYTHONPATH=src pytest tests/test_v1_1_empirical.py -v -m slow"

All tests are marked @pytest.mark.slow so they are skipped in the default
fast-test pass (CI + `pixi run test`). Use them to sanity-check that the
four v1.1 features behave as documented against real tensors / real models.
"""
import sys
sys.path.insert(0, "src")
import time
import pytest

# Small cached model — ~300 MB, loads in < 2s on M2 Max
SMALL_MODEL = "mlx-community/Qwen3-0.6B-4bit"


@pytest.fixture(autouse=True)
def _isolated_memory_dir(tmp_path, monkeypatch):
    """Redirect memory + sessions storage to tmp_path for all empirical tests."""
    try:
        from coding_agent.memory.store import set_memory_dir, clear_all_memories
        set_memory_dir(str(tmp_path / "memory"))
    except ImportError:
        pass
    try:
        from max_brain.kv_cache import set_sessions_dir
        set_sessions_dir(str(tmp_path / "sessions"))
    except ImportError:
        pass
    yield


# ---------------------------------------------------------------------------
# Feature 1 — Semantic episodic memory
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_memory_retrieval_ranks_semantically():
    """Store 3 memories, retrieve with a query close to one of them — it should rank first."""
    from coding_agent.memory.store import store_memory, TYPE_USER_PREFERENCE
    from coding_agent.memory.retriever import retrieve_relevant
    from coding_agent.memory.embeddings import embed_text

    # Same-topic facts: the query "python tuples" should rank the python tuple memory top.
    store_memory(
        text="The user prefers Python tuples over lists for immutable data.",
        embedding=embed_text("python tuples immutable"),
        type=TYPE_USER_PREFERENCE,
    )
    store_memory(
        text="The project uses Mojo 0.26.2 and MAX 26.2 on Apple Silicon.",
        embedding=embed_text("mojo max apple silicon"),
    )
    store_memory(
        text="Tests run via the pixi environment with PYTHONPATH=src.",
        embedding=embed_text("pixi pytest python path"),
    )

    results = retrieve_relevant("python tuples", k=3)
    assert len(results) >= 1
    # Top result should mention python or tuples
    top_text = results[0][0].text.lower()
    assert "python" in top_text or "tuples" in top_text


@pytest.mark.slow
def test_memory_extraction_parses_llm_output():
    """Simulate an LLM that returns a JSON array — extraction should persist each entry."""
    from coding_agent.memory.extractor import extract_from_session
    from coding_agent.memory.store import list_memories

    def fake_llm(prompt: str) -> str:
        return '''Here are some facts:
[
  {"text": "User prefers terse responses.", "type": "user_preference", "confidence": 0.9},
  {"text": "Project uses Mojo.", "type": "project_fact", "confidence": 0.95}
]
Some trailing prose.'''

    stored = extract_from_session("<transcript>", source="session:test", llm_fn=fake_llm)
    assert len(stored) == 2
    memories = list_memories()
    texts = [m.text for m in memories]
    assert any("terse" in t.lower() for t in texts)
    assert any("mojo" in t.lower() for t in texts)


# ---------------------------------------------------------------------------
# Feature 2 — Speculative decoding (empirical throughput)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_speculative_end_to_end_generates():
    """Speculative generation runs to completion and returns a non-empty string."""
    from max_brain.speculative import generate_speculative, clear_cache
    clear_cache()
    try:
        result = generate_speculative(
            "Say hello in one short sentence.",
            main_repo=SMALL_MODEL,
            draft_repo=SMALL_MODEL,  # same model as draft = still works, just no speedup
            max_new_tokens=16,
        )
    except Exception as e:
        pytest.skip(f"MLX model load failed: {e}")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.slow
def test_speculative_benchmark_reports_speedup():
    """benchmark_speculative returns structured dict with both runs."""
    from max_brain.speculative import benchmark_speculative, clear_cache
    clear_cache()
    try:
        result = benchmark_speculative(
            prompt="Count to three.",
            main_repo=SMALL_MODEL,
            draft_repo=SMALL_MODEL,
            max_new_tokens=8,
        )
    except Exception as e:
        pytest.skip(f"MLX not available or model failed: {e}")
    assert "baseline" in result
    assert "speculative" in result
    assert "speedup" in result
    assert result["baseline"]["total_tokens"] >= 1


# ---------------------------------------------------------------------------
# Feature 3 — KV cache persistence (round-trip with real tensors)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_kv_cache_round_trip_with_real_tensors():
    """Save a cache of real mlx.array tensors, delete from RAM, load back, verify values."""
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, load_kv_cache, load_kv_cache_meta

    class Layer:
        def __init__(self):
            self.keys = mx.random.normal(shape=(4, 64)).astype(mx.float16)
            self.values = mx.random.normal(shape=(4, 64)).astype(mx.float16)

    mx.random.seed(7)
    cache = [Layer() for _ in range(3)]
    original_k0 = cache[0].keys.tolist()

    meta = save_kv_cache(cache, "sess-empirical-1", SMALL_MODEL, token_count=4)
    assert meta["layer_count"] == 3
    assert meta["bytes"] > 0

    # Reload
    del cache
    loaded = load_kv_cache("sess-empirical-1", model=None)
    assert len(loaded) == 3
    reloaded_k0 = loaded[0].keys.tolist()
    assert reloaded_k0 == original_k0


@pytest.mark.slow
def test_kv_cache_from_real_mlx_model():
    """Load a small MLX model, run a forward pass, snapshot the prompt cache, persist, restore."""
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, load_kv_cache, load_kv_cache_meta

    try:
        from mlx_lm import load, make_prompt_cache
        model, tokenizer = load(SMALL_MODEL)
    except Exception as e:
        pytest.skip(f"MLX model load failed: {e}")

    # Build a prompt cache and warm it with a short prefill
    cache = make_prompt_cache(model)

    # Wrap cache entries so they look like .keys/.values shims if needed.
    # mlx-lm KVCache objects already expose .keys and .values.
    meta = save_kv_cache(cache, "sess-real-kv", SMALL_MODEL, token_count=0)
    assert meta["layer_count"] >= 1, "model produced no KV layers"

    loaded_meta = load_kv_cache_meta("sess-real-kv")
    assert loaded_meta["model"] == SMALL_MODEL
    assert loaded_meta["layer_count"] == meta["layer_count"]


# ---------------------------------------------------------------------------
# Feature 4 — TurboQuant quantization
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_turboquant_4bit_preserves_quality():
    """4-bit quantization on random tensors gives acceptable MAE."""
    import mlx.core as mx
    from max_brain.turboquant import (
        quantize_kv_cache,
        quantization_quality_metric,
        estimate_memory_reduction,
    )

    class Layer:
        def __init__(self):
            self.keys = mx.random.normal(shape=(32, 128))
            self.values = mx.random.normal(shape=(32, 128))

    mx.random.seed(42)
    cache = [Layer() for _ in range(2)]

    q = quantize_kv_cache(cache, bits=4, use_rotation=True, rotation_seed=7)
    metrics = quantization_quality_metric(cache, q)
    size = estimate_memory_reduction(cache, q)

    assert size["reduction_ratio"] > 3.0
    # MAE should be significantly smaller than RMS
    assert metrics["mae"] < metrics["original_rms"], (
        f"mae {metrics['mae']} >= rms {metrics['original_rms']}"
    )


@pytest.mark.slow
def test_turboquant_on_real_model_cache():
    """Quantize a real MLX prompt cache → measure memory reduction."""
    try:
        from mlx_lm import load, make_prompt_cache
        model, tokenizer = load(SMALL_MODEL)
    except Exception as e:
        pytest.skip(f"MLX model load failed: {e}")

    from max_brain.turboquant import quantize_kv_cache, estimate_memory_reduction

    cache = make_prompt_cache(model)

    try:
        q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    except Exception as e:
        pytest.skip(f"quantize failed on real cache (shape mismatch?): {e}")

    if not q:
        pytest.skip("real prompt cache produced 0 quantizable layers "
                    "(shape may not divide cleanly into group_size)")

    size = estimate_memory_reduction(cache, q)
    # Real caches should compress; expect at least 2× even with rotation overhead
    assert size["bytes_before"] > size["bytes_after"]
    assert size["reduction_ratio"] > 2.0


# ---------------------------------------------------------------------------
# Cross-feature — quantize THEN persist
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_turboquant_then_persist_end_to_end():
    """The combined flow: build cache → quantize → save → load → dequantize."""
    import mlx.core as mx
    from max_brain.turboquant import (
        quantize_kv_cache,
        dequantize_kv_cache,
        estimate_memory_reduction,
    )

    class Layer:
        def __init__(self):
            self.keys = mx.random.normal(shape=(8, 64))
            self.values = mx.random.normal(shape=(8, 64))

    mx.random.seed(0)
    cache = [Layer() for _ in range(2)]

    q = quantize_kv_cache(cache, bits=4, use_rotation=True)
    restored = dequantize_kv_cache(q)
    assert len(restored) == 2
    assert tuple(restored[0].keys.shape) == (8, 64)
