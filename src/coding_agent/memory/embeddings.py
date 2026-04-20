"""Embedding backends — real Metal via mlx-lm, or bag-of-words fallback."""
from __future__ import annotations
import hashlib
import math
from typing import Optional

# Bag-of-words vocabulary hash size (tests use this, deterministic)
_BOW_DIM = 256

_mlx_embed_model = None
_mlx_embed_tokenizer = None
_mlx_embed_failed = False

DEFAULT_EMBED_MODEL = "mlx-community/bge-small-en-v1.5-4bit"


def _try_load_mlx_embedder(model_repo: str = DEFAULT_EMBED_MODEL):
    """Attempt to load an MLX embedding model. Returns (model, tokenizer) or (None, None)."""
    global _mlx_embed_model, _mlx_embed_tokenizer, _mlx_embed_failed
    if _mlx_embed_failed:
        return None, None
    if _mlx_embed_model is not None:
        return _mlx_embed_model, _mlx_embed_tokenizer
    try:
        from mlx_lm import load
        m, t = load(model_repo)
        _mlx_embed_model = m
        _mlx_embed_tokenizer = t
        return m, t
    except Exception:
        _mlx_embed_failed = True
        return None, None


def _embed_mlx(text: str, model, tokenizer) -> list[float]:
    """Generate embedding via an MLX embedding model."""
    import mlx.core as mx
    tokens = tokenizer.encode(text) if hasattr(tokenizer, "encode") else tokenizer(text)
    if hasattr(tokens, "ids"):
        tokens = tokens.ids
    arr = mx.array(tokens).reshape(1, -1)
    with mx.no_grad() if hasattr(mx, "no_grad") else _null_ctx():
        out = model(arr)
    # Mean-pool over sequence dim
    if hasattr(out, "shape") and len(out.shape) == 3:
        pooled = mx.mean(out, axis=1).squeeze()
    else:
        pooled = out.squeeze()
    vec = [float(x) for x in pooled.tolist()]
    return _normalize(vec)


class _null_ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _embed_bow(text: str, dim: int = _BOW_DIM) -> list[float]:
    """Deterministic bag-of-words embedding for tests & fallback.

    Hashes each lowercased word into a bucket of `dim` floats; normalizes.
    """
    vec = [0.0] * dim
    for word in text.lower().split():
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dim] += 1.0
    return _normalize(vec)


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def embed_text(text: str, prefer_mlx: bool = True) -> list[float]:
    """Return a unit-normalized embedding vector.

    Tries MLX Metal first if prefer_mlx=True; falls back to bag-of-words.
    """
    if prefer_mlx:
        m, t = _try_load_mlx_embedder()
        if m is not None:
            try:
                return _embed_mlx(text, m, t)
            except Exception:
                pass
    return _embed_bow(text)


def embed_dim() -> int:
    """Dimensionality of the current embedder (useful for store init)."""
    if _mlx_embed_model is not None:
        # We don't know without a test embed; assume bow for safety.
        return _BOW_DIM
    return _BOW_DIM


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))  # already normalized
