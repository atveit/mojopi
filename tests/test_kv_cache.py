"""Tests for max_brain/kv_cache.py — KV cache persistence for sessions.

Uses mock cache objects (MockLayer with .keys/.values), no model weights.
"""
import sys
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolated_sessions_dir(tmp_path):
    from max_brain.kv_cache import set_sessions_dir
    set_sessions_dir(str(tmp_path))
    yield


class MockTensor:
    def __init__(self, shape=(8, 4), dtype="float16"):
        self.shape = shape
        self.dtype = dtype

    def tolist(self):
        return [[0.0] * self.shape[1] for _ in range(self.shape[0])]


class MockLayer:
    def __init__(self, shape=(8, 4), dtype="float16"):
        self.keys = MockTensor(shape, dtype)
        self.values = MockTensor(shape, dtype)


def test_module_importable():
    from max_brain import kv_cache
    assert hasattr(kv_cache, "save_kv_cache")
    assert hasattr(kv_cache, "load_kv_cache")
    assert hasattr(kv_cache, "cache_path_for_session")
    assert hasattr(kv_cache, "estimate_cache_size")


def test_cache_path_derivation(tmp_path):
    from max_brain.kv_cache import cache_path_for_session, set_sessions_dir
    set_sessions_dir(str(tmp_path))
    p = cache_path_for_session("abc-123")
    assert "abc-123" in str(p)
    assert "kv_cache" in str(p)


def test_estimate_cache_size_empty():
    from max_brain.kv_cache import estimate_cache_size
    assert estimate_cache_size([]) == 0
    assert estimate_cache_size(None) == 0


def test_estimate_cache_size_fp16():
    from max_brain.kv_cache import estimate_cache_size
    layers = [MockLayer(shape=(8, 4), dtype="float16") for _ in range(3)]
    # 3 layers × (8*4*2) × 2 tensors (keys + values) = 3 × 64 × 2 = 384
    assert estimate_cache_size(layers) == 3 * 8 * 4 * 2 * 2


def test_estimate_cache_size_fp32():
    from max_brain.kv_cache import estimate_cache_size
    layers = [MockLayer(shape=(4, 4), dtype="float32") for _ in range(2)]
    # 2 × (4*4*4) × 2 = 256
    assert estimate_cache_size(layers) == 2 * 4 * 4 * 4 * 2


def test_load_nonexistent_returns_none():
    from max_brain.kv_cache import load_kv_cache_meta
    assert load_kv_cache_meta("no-such-session") is None


def test_load_nonexistent_raises_filenotfound():
    from max_brain.kv_cache import load_kv_cache
    with pytest.raises(FileNotFoundError):
        load_kv_cache("no-such-session", model=None)


def test_delete_returns_false_when_no_cache():
    from max_brain.kv_cache import delete_kv_cache
    assert delete_kv_cache("no-such-session-xyz") is False


def test_list_cached_sessions_empty():
    from max_brain.kv_cache import list_cached_sessions
    assert list_cached_sessions() == []


def test_save_and_load_round_trip(monkeypatch):
    """Save real MLX arrays + restore them via mx.savez/mx.load."""
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, load_kv_cache, load_kv_cache_meta

    # Build a realistic cache using actual mlx arrays.
    class RealLayer:
        def __init__(self):
            self.keys = mx.array([[1.0, 2.0], [3.0, 4.0]])
            self.values = mx.array([[5.0, 6.0], [7.0, 8.0]])

    cache = [RealLayer(), RealLayer()]

    meta = save_kv_cache(cache, session_id="s1", model_repo="test-model", token_count=42)
    assert meta["model"] == "test-model"
    assert meta["token_count"] == 42
    assert meta["layer_count"] == 2

    restored_meta = load_kv_cache_meta("s1")
    assert restored_meta is not None
    assert restored_meta["token_count"] == 42

    layers = load_kv_cache("s1", model=None)
    assert len(layers) == 2
    # Verify values survived
    k0 = layers[0].keys
    v0 = layers[0].values
    assert k0.tolist() == [[1.0, 2.0], [3.0, 4.0]]
    assert v0.tolist() == [[5.0, 6.0], [7.0, 8.0]]


def test_save_creates_meta_json():
    """Save writes meta.json with required fields."""
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, cache_meta_path
    import json

    class L:
        def __init__(self):
            self.keys = mx.array([[1.0]])
            self.values = mx.array([[2.0]])

    save_kv_cache([L()], session_id="s2", model_repo="m", token_count=10)
    meta_path = cache_meta_path("s2")
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert "model" in meta
    assert "token_count" in meta
    assert "sha256" in meta
    assert "created" in meta


def test_list_cached_sessions_after_save():
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, list_cached_sessions

    class L:
        def __init__(self):
            self.keys = mx.array([[1.0]])
            self.values = mx.array([[2.0]])

    save_kv_cache([L()], "sess-aaa", "m", 1)
    save_kv_cache([L()], "sess-bbb", "m", 2)
    sessions = list_cached_sessions()
    assert "sess-aaa" in sessions
    assert "sess-bbb" in sessions


def test_delete_removes_cache():
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, delete_kv_cache, load_kv_cache_meta

    class L:
        def __init__(self):
            self.keys = mx.array([[1.0]])
            self.values = mx.array([[2.0]])

    save_kv_cache([L()], "todelete", "m", 1)
    assert load_kv_cache_meta("todelete") is not None
    assert delete_kv_cache("todelete") is True
    assert load_kv_cache_meta("todelete") is None
