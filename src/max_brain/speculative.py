"""Speculative decoding via mlx-lm's draft_model kwarg.

Pairs a small draft model with a larger main model: the draft proposes several
tokens in a forward pass, the main verifies them in a single batched pass.
Same output distribution, 1.5-2x faster on typical workloads.

Falls back to plain generate_mlx if the draft model can't be loaded.
"""
from __future__ import annotations
import time
from typing import Optional

DEFAULT_MAIN = "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
DEFAULT_DRAFT = "mlx-community/Llama-3.2-1B-Instruct-4bit"

# Caches keyed by (main_repo, draft_repo) tuple
_spec_cache: dict = {}


def _load_pair(main_repo: str, draft_repo: str):
    """Load (main_model, main_tokenizer, draft_model) triple, cached."""
    key = (main_repo, draft_repo)
    if key in _spec_cache:
        return _spec_cache[key]
    from mlx_lm import load
    main_model, tokenizer = load(main_repo)
    draft_model = None
    try:
        draft_model, _ = load(draft_repo)
    except Exception as e:
        print(f"[speculative] draft model {draft_repo} failed to load: {e}")
    triple = (main_model, tokenizer, draft_model)
    _spec_cache[key] = triple
    return triple


def is_available() -> bool:
    """Return True if mlx-lm and mlx are importable."""
    try:
        import mlx_lm  # noqa
        import mlx.core  # noqa
        return True
    except ImportError:
        return False


def generate_speculative(
    prompt: str,
    main_repo: str = DEFAULT_MAIN,
    draft_repo: str = DEFAULT_DRAFT,
    max_new_tokens: int = 512,
) -> str:
    """Generate using speculative decoding. Falls back to regular on draft failure."""
    from mlx_lm import generate
    main_model, tokenizer, draft_model = _load_pair(main_repo, draft_repo)
    if draft_model is None:
        return generate(main_model, tokenizer, prompt, max_tokens=max_new_tokens)
    return generate(main_model, tokenizer, prompt, max_tokens=max_new_tokens, draft_model=draft_model)


def stream_speculative(
    prompt: str,
    main_repo: str = DEFAULT_MAIN,
    draft_repo: str = DEFAULT_DRAFT,
    max_new_tokens: int = 512,
):
    """Stream tokens via speculative decoding; yields text chunks."""
    from mlx_lm import stream_generate
    main_model, tokenizer, draft_model = _load_pair(main_repo, draft_repo)
    kwargs = {"max_tokens": max_new_tokens}
    if draft_model is not None:
        kwargs["draft_model"] = draft_model
    for response in stream_generate(main_model, tokenizer, prompt, **kwargs):
        yield response.text


def _run_stream(stream_fn, prompt: str, max_new_tokens: int) -> dict:
    """Helper: time a stream and return {ttft_ms, throughput_tok_s, total_tokens, total_time_s}."""
    t0 = time.perf_counter()
    first_token_time = None
    tokens = []
    for chunk in stream_fn():
        if first_token_time is None:
            first_token_time = time.perf_counter() - t0
        tokens.append(chunk)
    total = time.perf_counter() - t0
    return {
        "ttft_ms": round((first_token_time or total) * 1000, 1),
        "throughput_tok_s": round(len(tokens) / total if total > 0 else 0, 1),
        "total_tokens": len(tokens),
        "total_time_s": round(total, 3),
    }


def benchmark_speculative(
    prompt: str = "Explain the difference between a list and a tuple in Python.",
    main_repo: str = DEFAULT_MAIN,
    draft_repo: str = DEFAULT_DRAFT,
    max_new_tokens: int = 64,
) -> dict:
    """Compare speculative vs baseline generation on the same prompt.

    Returns:
        {
          "main_model": ..., "draft_model": ...,
          "baseline": {ttft_ms, throughput_tok_s, total_tokens, total_time_s},
          "speculative": {ttft_ms, throughput_tok_s, total_tokens, total_time_s},
          "speedup": float,
        }
    """
    from mlx_lm import stream_generate
    main_model, tokenizer, draft_model = _load_pair(main_repo, draft_repo)

    # Baseline
    def _baseline():
        for r in stream_generate(main_model, tokenizer, prompt, max_tokens=max_new_tokens):
            yield r.text

    baseline = _run_stream(_baseline, prompt, max_new_tokens)

    if draft_model is None:
        return {
            "main_model": main_repo,
            "draft_model": None,
            "baseline": baseline,
            "speculative": baseline,
            "speedup": 1.0,
            "note": "draft model unavailable - speculative == baseline",
        }

    def _spec():
        for r in stream_generate(main_model, tokenizer, prompt, max_tokens=max_new_tokens, draft_model=draft_model):
            yield r.text

    spec = _run_stream(_spec, prompt, max_new_tokens)
    baseline_tps = baseline["throughput_tok_s"] or 1.0
    speedup = spec["throughput_tok_s"] / baseline_tps if baseline_tps > 0 else 1.0

    return {
        "main_model": main_repo,
        "draft_model": draft_repo,
        "baseline": baseline,
        "speculative": spec,
        "speedup": round(speedup, 2),
    }


def clear_cache() -> None:
    """Drop the cached model pair (useful in tests)."""
    _spec_cache.clear()
