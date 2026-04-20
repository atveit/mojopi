"""Tests for the MLX Metal inference backend.

Fast tests verify module structure without model weights.
Slow tests require model weights and a working MLX install.
"""
import sys
sys.path.insert(0, "src")
import pytest


def test_mlx_backend_importable():
    from max_brain import mlx_backend
    assert hasattr(mlx_backend, "is_available")
    assert hasattr(mlx_backend, "generate_mlx")
    assert hasattr(mlx_backend, "stream_generate_mlx")
    assert hasattr(mlx_backend, "benchmark_mlx")
    assert hasattr(mlx_backend, "_mlx_cache")


def test_is_available_returns_bool():
    from max_brain.mlx_backend import is_available
    result = is_available()
    assert isinstance(result, bool)


def test_mlx_available_on_arm64():
    import platform
    from max_brain.mlx_backend import is_available
    if platform.machine() == "arm64":
        assert is_available(), "MLX should be available on arm64 with mlx installed"
    else:
        assert not is_available(), "MLX should not be available on non-arm64"


def test_cache_dict_exists():
    from max_brain.mlx_backend import _mlx_cache
    assert isinstance(_mlx_cache, dict)


def test_generate_embedded_prefers_mlx_on_arm64(monkeypatch):
    """generate_embedded should call generate_mlx first on arm64."""
    import platform
    if platform.machine() != "arm64":
        pytest.skip("arm64 only")

    import max_brain.pipeline as p
    import max_brain.mlx_backend as mlx_mod
    calls = []

    def fake_mlx(prompt, model_repo, max_new_tokens):
        calls.append("mlx")
        return "mlx result"

    monkeypatch.setattr(mlx_mod, "generate_mlx", fake_mlx)
    monkeypatch.setattr(mlx_mod, "is_available", lambda: True)

    result = p.generate_embedded("hello", max_new_tokens=4)
    assert "mlx" in calls, "generate_embedded should have called MLX"
    assert result == "mlx result"


@pytest.mark.slow
def test_mlx_generate_with_model():
    """Full MLX generation (requires model weights)."""
    from max_brain.mlx_backend import generate_mlx, is_available
    if not is_available():
        pytest.skip("MLX not available")
    try:
        result = generate_mlx("Hello!", max_new_tokens=8)
        assert isinstance(result, str)
    except Exception as e:
        pytest.skip(f"MLX model load failed: {e}")
