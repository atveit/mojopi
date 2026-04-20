"""MLX Metal inference backend for Apple Silicon.

Uses Apple's MLX framework to run inference natively on the Metal GPU,
bypassing MAX's CPU path. On M-series chips this is typically 3–5× faster
than MAX on CPU.

Model loading: mlx-lm can load HuggingFace GGUF repos and native MLX-format
repos. Native MLX quantized models (e.g. mlx-community/*-4bit) load faster
and use less memory than GGUF.

The cached (model, tokenizer) tuple is keyed by model_repo so subsequent
calls to the same model skip the load cost.
"""
from __future__ import annotations
import platform

_is_arm64 = platform.machine() == "arm64"

# (model, tokenizer) cache keyed by model_repo
_mlx_cache: dict = {}


def _is_available() -> bool:
    try:
        import mlx.core  # noqa: F401
        import mlx_lm   # noqa: F401
        return True
    except ImportError:
        return False


def is_available() -> bool:
    """Return True if MLX and mlx-lm are importable on this machine."""
    return _is_arm64 and _is_available()


def get_or_load_model(model_repo: str):
    """Load (model, tokenizer) once and cache by model_repo."""
    if model_repo in _mlx_cache:
        return _mlx_cache[model_repo]
    from mlx_lm import load
    model, tokenizer = load(model_repo)
    _mlx_cache[model_repo] = (model, tokenizer)
    return model, tokenizer


def generate_mlx(
    prompt: str,
    model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 512,
    verbose: bool = False,
) -> str:
    """Generate text via MLX Metal.

    Returns the generated text string. Raises on load or generation failure
    so callers can fall back to the MAX CPU path.
    """
    from mlx_lm import generate
    model, tokenizer = get_or_load_model(model_repo)
    return generate(model, tokenizer, prompt, max_tokens=max_new_tokens, verbose=verbose)


def stream_generate_mlx(
    prompt: str,
    model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 512,
):
    """Stream tokens from MLX Metal. Yields text chunks as they arrive."""
    from mlx_lm import stream_generate
    model, tokenizer = get_or_load_model(model_repo)
    for response in stream_generate(model, tokenizer, prompt, max_tokens=max_new_tokens):
        yield response.text


def benchmark_mlx(
    prompt: str = "Explain the difference between a list and a tuple in Python.",
    model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 64,
) -> dict:
    """Run a quick benchmark and return timing metrics."""
    import time
    from mlx_lm import stream_generate

    model, tokenizer = get_or_load_model(model_repo)

    t0 = time.perf_counter()
    first_token_time = None
    tokens = []

    for response in stream_generate(model, tokenizer, prompt, max_tokens=max_new_tokens):
        if first_token_time is None:
            first_token_time = time.perf_counter() - t0
        tokens.append(response.text)

    total_time = time.perf_counter() - t0
    n = len(tokens)
    return {
        "backend": "mlx-metal",
        "model": model_repo,
        "ttft_ms": round((first_token_time or total_time) * 1000, 1),
        "throughput_tok_s": round(n / total_time if total_time > 0 else 0, 1),
        "total_tokens": n,
        "total_time_s": round(total_time, 3),
    }
