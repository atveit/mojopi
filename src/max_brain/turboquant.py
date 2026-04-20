"""TurboQuant-style KV cache quantization for MLX.

Reduces KV cache memory by 4x (4-bit) or 8x (2-bit) with minimal quality loss
when combined with random orthogonal rotation. The rotation seed is stored
in the layer metadata, so recovery is deterministic.

Quantized layer shape:
  QuantizedLayer(
    k_q: mx.array (int4 or int2 packed),
    k_scales: mx.array,
    k_biases: mx.array,
    v_q: ...,
    v_scales: ...,
    v_biases: ...,
    rotation_seed: int | None,
    bits: int,
    group_size: int,
    original_shape: tuple,
    original_dtype: str,
  )
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any

DEFAULT_BITS = 4
DEFAULT_GROUP_SIZE = 64


@dataclass
class QuantizedLayer:
    k_q: Any = None
    k_scales: Any = None
    k_biases: Any = None
    v_q: Any = None
    v_scales: Any = None
    v_biases: Any = None
    rotation_seed: Optional[int] = None
    bits: int = DEFAULT_BITS
    group_size: int = DEFAULT_GROUP_SIZE
    original_shape: tuple = field(default_factory=tuple)
    original_dtype: str = "float16"

    # Restored (post-dequant) .keys/.values compatibility shims
    @property
    def keys(self):
        return self.k_q

    @property
    def values(self):
        return self.v_q


def _import_mx():
    import mlx.core as mx
    return mx


def _make_rotation_matrix(dim: int, seed: Optional[int]):
    """Random orthogonal matrix [dim, dim] seeded for determinism."""
    mx = _import_mx()
    if seed is not None:
        mx.random.seed(seed)
    # Generate random normal, QR decompose, use Q (orthogonal).
    g = mx.random.normal(shape=(dim, dim))
    # Prefer MLX's linalg.qr if available; fall back to numpy otherwise.
    try:
        qr = getattr(getattr(mx, "linalg", None), "qr", None)
        if qr is not None:
            q, _ = qr(g, stream=mx.cpu) if _qr_takes_stream(qr) else qr(g)
            return q
    except Exception:
        pass
    import numpy as np
    g_np = np.array(g)
    q, _ = np.linalg.qr(g_np)
    return mx.array(q)


def _qr_takes_stream(qr_fn) -> bool:
    # mx.linalg.qr in some MLX versions requires stream=mx.cpu. Probe cheaply.
    try:
        import inspect
        sig = inspect.signature(qr_fn)
        return "stream" in sig.parameters
    except Exception:
        return False


def _apply_rotation(tensor, R):
    """Apply orthogonal rotation along the last dim: X @ R."""
    mx = _import_mx()
    # Cast R to the tensor's dtype to keep matmul dtype-consistent.
    try:
        R_cast = R.astype(tensor.dtype)
    except Exception:
        R_cast = R
    return tensor @ R_cast


def _apply_inverse_rotation(tensor, R):
    """Apply R^T (inverse of orthogonal R)."""
    mx = _import_mx()
    try:
        R_cast = R.astype(tensor.dtype)
    except Exception:
        R_cast = R
    return tensor @ R_cast.T


def quantize_kv_cache(
    cache: list,
    bits: int = DEFAULT_BITS,
    group_size: int = DEFAULT_GROUP_SIZE,
    use_rotation: bool = True,
    rotation_seed: int = 42,
) -> list:
    """Quantize a full KV cache layer by layer.

    Args:
        cache: list of objects with .keys and .values MLX arrays
        bits: 2, 3, 4, or 8
        group_size: quantization group size
        use_rotation: apply TurboQuant rotation before quantizing
        rotation_seed: deterministic seed for the rotation matrix
    Returns list of QuantizedLayer objects.
    """
    mx = _import_mx()
    if cache is None:
        return []
    result: list[QuantizedLayer] = []
    for layer in cache:
        k = getattr(layer, "keys", None)
        v = getattr(layer, "values", None)
        if k is None or v is None:
            continue
        original_shape = tuple(k.shape) if hasattr(k, "shape") else ()
        original_dtype = str(getattr(k, "dtype", "float16"))

        k_in, v_in = k, v
        seed_to_store: Optional[int] = None
        if use_rotation and len(original_shape) >= 2:
            last_dim = original_shape[-1]
            R = _make_rotation_matrix(last_dim, rotation_seed)
            k_in = _apply_rotation(k, R)
            v_in = _apply_rotation(v, R)
            seed_to_store = rotation_seed

        k_q, k_scales, k_biases = mx.quantize(k_in, group_size=group_size, bits=bits)
        v_q, v_scales, v_biases = mx.quantize(v_in, group_size=group_size, bits=bits)

        result.append(QuantizedLayer(
            k_q=k_q, k_scales=k_scales, k_biases=k_biases,
            v_q=v_q, v_scales=v_scales, v_biases=v_biases,
            rotation_seed=seed_to_store,
            bits=bits, group_size=group_size,
            original_shape=original_shape, original_dtype=original_dtype,
        ))
    return result


def dequantize_kv_cache(quantized: list) -> list:
    """Reverse quantization -> list of (keys, values) compatible shims."""
    mx = _import_mx()

    class _RestoredLayer:
        __slots__ = ("keys", "values")
        def __init__(self, k, v):
            self.keys = k
            self.values = v

    if quantized is None:
        return []
    result = []
    for q in quantized:
        k = mx.dequantize(q.k_q, q.k_scales, q.k_biases,
                          group_size=q.group_size, bits=q.bits)
        v = mx.dequantize(q.v_q, q.v_scales, q.v_biases,
                          group_size=q.group_size, bits=q.bits)
        if q.rotation_seed is not None and len(q.original_shape) >= 2:
            R = _make_rotation_matrix(q.original_shape[-1], q.rotation_seed)
            k = _apply_inverse_rotation(k, R)
            v = _apply_inverse_rotation(v, R)
        result.append(_RestoredLayer(k, v))
    return result


def estimate_memory_reduction(
    original: list,
    quantized: list,
) -> dict:
    """Report memory footprint before / after quantization."""
    def _fp16_bytes(cache):
        total = 0
        for layer in cache or []:
            for attr in ("keys", "values"):
                t = getattr(layer, attr, None)
                if t is None or not hasattr(t, "shape"):
                    continue
                n = 1
                for d in t.shape:
                    n *= int(d)
                total += n * 2  # fp16
        return total

    def _quantized_bytes(cache):
        total = 0
        for layer in cache or []:
            # Quantized arrays: bits/8 per element + scales + biases (fp16 each, 1 per group)
            for attr_q, attr_s, attr_b in (("k_q", "k_scales", "k_biases"),
                                            ("v_q", "v_scales", "v_biases")):
                q = getattr(layer, attr_q, None)
                if q is None or not hasattr(q, "shape"):
                    continue
                # Quantized storage: original_numel * bits / 8 (packed)
                orig = layer.original_shape
                numel = 1
                for d in orig:
                    numel *= int(d)
                total += (numel * layer.bits) // 8
                # Scales + biases: one per group
                groups = max(1, numel // layer.group_size)
                total += groups * 2 * 2  # fp16 scales + fp16 biases
        return total

    before = _fp16_bytes(original)
    after = _quantized_bytes(quantized)
    reduction = before / after if after > 0 else 0.0
    return {
        "bytes_before": before,
        "bytes_after": after,
        "reduction_ratio": round(reduction, 2),
        "mb_saved": round((before - after) / (1024 * 1024), 2),
    }


def quantization_quality_metric(original: list, quantized: list) -> dict:
    """Compare original vs dequantize(quantize(original)) -- mean absolute error.

    Returns {"mae": float, "max_abs_err": float, "original_rms": float}.
    Higher MAE -> worse reconstruction; TurboQuant targets < 1% of RMS.
    """
    mx = _import_mx()
    restored = dequantize_kv_cache(quantized)
    total_err = 0.0
    max_err = 0.0
    total_rms = 0.0
    n_samples = 0

    for orig_layer, rest_layer in zip(original, restored):
        for attr in ("keys", "values"):
            o = getattr(orig_layer, attr)
            r = getattr(rest_layer, attr)
            # Ensure dtypes match before subtracting.
            try:
                if o.dtype != r.dtype:
                    r = r.astype(o.dtype)
            except Exception:
                pass
            diff = o - r
            abs_diff = mx.abs(diff)
            mae = float(mx.mean(abs_diff).item())
            mx_val = float(mx.max(abs_diff).item())
            rms = float(mx.sqrt(mx.mean(o * o)).item())
            total_err += mae
            total_rms += rms
            if mx_val > max_err:
                max_err = mx_val
            n_samples += 1

    return {
        "mae": round(total_err / n_samples if n_samples else 0.0, 6),
        "max_abs_err": round(max_err, 6),
        "original_rms": round(total_rms / n_samples if n_samples else 0.0, 6),
    }
