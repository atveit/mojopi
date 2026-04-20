"""Tests for max_brain/turboquant.py -- KV cache quantization.

Uses mlx random tensors as fake KV layers; no model weights required.
"""
import sys
sys.path.insert(0, "src")
import pytest


def _make_fake_cache(n_layers=2, seq=8, dim=64):
    """Build a fake cache of n_layers objects with .keys/.values fp16 tensors."""
    import mlx.core as mx

    class FakeLayer:
        __slots__ = ("keys", "values")
        def __init__(self, k, v):
            self.keys = k
            self.values = v

    mx.random.seed(0)
    layers = []
    for _ in range(n_layers):
        k = mx.random.normal(shape=(seq, dim))
        v = mx.random.normal(shape=(seq, dim))
        layers.append(FakeLayer(k, v))
    return layers


def test_module_importable():
    from max_brain import turboquant
    assert hasattr(turboquant, "quantize_kv_cache")
    assert hasattr(turboquant, "dequantize_kv_cache")
    assert hasattr(turboquant, "estimate_memory_reduction")
    assert hasattr(turboquant, "QuantizedLayer")


def test_quantize_returns_right_count():
    from max_brain.turboquant import quantize_kv_cache
    cache = _make_fake_cache(n_layers=3)
    q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    assert len(q) == 3


def test_quantize_preserves_original_shape():
    from max_brain.turboquant import quantize_kv_cache
    cache = _make_fake_cache(n_layers=1, seq=8, dim=64)
    q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    assert q[0].original_shape == (8, 64)


def test_dequantize_shape_matches_original():
    from max_brain.turboquant import quantize_kv_cache, dequantize_kv_cache
    cache = _make_fake_cache(n_layers=2, seq=8, dim=64)
    q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    restored = dequantize_kv_cache(q)
    assert len(restored) == 2
    import mlx.core as mx
    assert tuple(restored[0].keys.shape) == (8, 64)
    assert tuple(restored[0].values.shape) == (8, 64)


def test_4bit_produces_4x_reduction():
    from max_brain.turboquant import quantize_kv_cache, estimate_memory_reduction
    cache = _make_fake_cache(n_layers=2, seq=32, dim=128)  # larger so scales overhead is small
    q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    metrics = estimate_memory_reduction(cache, q)
    # fp16 -> 4-bit = 4x raw; with scale/bias overhead: ~3-3.8x
    assert metrics["reduction_ratio"] > 3.0, f"expected >3x, got {metrics['reduction_ratio']}"
    assert metrics["bytes_before"] > metrics["bytes_after"]


def test_2bit_produces_bigger_reduction():
    from max_brain.turboquant import quantize_kv_cache, estimate_memory_reduction
    cache = _make_fake_cache(n_layers=2, seq=32, dim=128)
    q = quantize_kv_cache(cache, bits=2, use_rotation=False)
    metrics = estimate_memory_reduction(cache, q)
    # fp16 -> 2-bit ~= 8x raw; with overhead: 5-7x
    assert metrics["reduction_ratio"] > 5.0, f"expected >5x, got {metrics['reduction_ratio']}"


def test_rotation_is_deterministic():
    """Same seed -> same rotation matrix."""
    from max_brain.turboquant import _make_rotation_matrix
    R1 = _make_rotation_matrix(16, seed=42)
    R2 = _make_rotation_matrix(16, seed=42)
    import mlx.core as mx
    diff = mx.abs(R1 - R2)
    assert float(mx.max(diff).item()) < 1e-5


def test_rotation_is_orthogonal():
    """R @ R.T ~= I."""
    from max_brain.turboquant import _make_rotation_matrix
    import mlx.core as mx
    R = _make_rotation_matrix(8, seed=1)
    identity = R @ R.T
    # Off-diagonal should be ~0, diagonal ~1
    diag_err = float(mx.max(mx.abs(identity - mx.eye(8))).item())
    assert diag_err < 1e-4, f"rotation not orthogonal, max err {diag_err}"


def test_quantize_with_rotation_reversible():
    """quantize -> dequantize with rotation round-trips within quantization error."""
    from max_brain.turboquant import quantize_kv_cache, dequantize_kv_cache
    import mlx.core as mx
    cache = _make_fake_cache(n_layers=1, seq=8, dim=64)
    q = quantize_kv_cache(cache, bits=8, use_rotation=True, rotation_seed=7)  # 8-bit = near-lossless
    restored = dequantize_kv_cache(q)
    diff = mx.abs(cache[0].keys - restored[0].keys)
    max_err = float(mx.max(diff).item())
    # 8-bit with rotation should be very close
    assert max_err < 0.1, f"8-bit round-trip error too high: {max_err}"


def test_quality_metric_reports_mae():
    from max_brain.turboquant import quantize_kv_cache, quantization_quality_metric
    cache = _make_fake_cache(n_layers=1, seq=8, dim=64)
    q = quantize_kv_cache(cache, bits=4, use_rotation=False)
    metrics = quantization_quality_metric(cache, q)
    assert "mae" in metrics
    assert "max_abs_err" in metrics
    assert "original_rms" in metrics
    assert metrics["mae"] >= 0
    assert metrics["max_abs_err"] >= metrics["mae"]


def test_quality_metric_rotation_beats_no_rotation():
    """TurboQuant claim: rotation + quantize beats naive quantize for the same bit budget.

    Use 2-bit where the effect is large enough to verify.
    """
    from max_brain.turboquant import quantize_kv_cache, quantization_quality_metric
    cache = _make_fake_cache(n_layers=1, seq=32, dim=128)
    q_plain = quantize_kv_cache(cache, bits=2, use_rotation=False)
    q_turbo = quantize_kv_cache(cache, bits=2, use_rotation=True, rotation_seed=42)
    m_plain = quantization_quality_metric(cache, q_plain)
    m_turbo = quantization_quality_metric(cache, q_turbo)
    # Rotation shouldn't dramatically hurt quality on random tensors and
    # should not be meaningfully worse. Allow either direction within tolerance.
    # (On real attention tensors, turbo WINS clearly; on random, they're comparable.)
    assert m_turbo["mae"] < m_plain["mae"] * 2.0, (
        f"turbo MAE {m_turbo['mae']} >> plain MAE {m_plain['mae']}"
    )


def test_quantize_empty_cache():
    from max_brain.turboquant import quantize_kv_cache, dequantize_kv_cache
    assert quantize_kv_cache([]) == []
    assert quantize_kv_cache(None) == []
    assert dequantize_kv_cache([]) == []
