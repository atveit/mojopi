"""KV cache persistence for resumable sessions.

MLX's per-layer prompt cache can be serialized to disk so session resume
skips the re-prefill cost entirely. One directory per session, one .npz
per layer, plus a meta.json with model + token count for validation.

Path layout:
  ~/.pi/sessions/<session_id>/kv_cache/
    meta.json
    layer_000.npz
    layer_001.npz
    ...
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

SESSIONS_DIR = Path("~/.pi/sessions").expanduser()


def cache_path_for_session(session_id: str) -> Path:
    """Return the kv_cache directory path for a session_id.

    Does NOT create the directory — use mkdir(parents=True, exist_ok=True) before writing.
    """
    return SESSIONS_DIR / session_id / "kv_cache"


def cache_meta_path(session_id: str) -> Path:
    return cache_path_for_session(session_id) / "meta.json"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def estimate_cache_size(cache: list) -> int:
    """Return an estimate in bytes of the cache's memory footprint.

    Accepts either real MLX KVCache objects (with .keys/.values arrays) or
    mock objects with .shape and .dtype attributes. Unknown shapes count as 0.
    """
    total = 0
    for layer in cache or []:
        for attr in ("keys", "values"):
            t = getattr(layer, attr, None)
            if t is None:
                continue
            shape = getattr(t, "shape", None)
            if shape is None:
                continue
            n = 1
            for d in shape:
                n *= int(d)
            dtype = getattr(t, "dtype", None)
            # Best-effort bytes-per-element
            bpe = 2  # default fp16
            if dtype is not None:
                dtype_name = str(dtype)
                if "float32" in dtype_name or "int32" in dtype_name:
                    bpe = 4
                elif "int8" in dtype_name or "uint8" in dtype_name:
                    bpe = 1
                elif "int64" in dtype_name or "float64" in dtype_name:
                    bpe = 8
            total += n * bpe
    return total


def save_kv_cache(
    cache: list,
    session_id: str,
    model_repo: str,
    token_count: int,
) -> dict:
    """Serialize an MLX prompt cache for a session.

    Returns a metadata dict containing path, layer_count, bytes, and sha256.
    """
    import mlx.core as mx

    out_dir = cache_path_for_session(session_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    layer_count = 0
    hash_input = b""

    for i, layer in enumerate(cache or []):
        k = getattr(layer, "keys", None)
        v = getattr(layer, "values", None)
        if k is None or v is None:
            continue
        path = out_dir / f"layer_{i:03d}.npz"
        # mx.savez takes a dict of arrays
        mx.savez(str(path), k=k, v=v)
        layer_count += 1
        try:
            hash_input += bytes(path.name, "utf-8")
        except Exception:
            pass

    meta = {
        "model": model_repo,
        "token_count": int(token_count),
        "layer_count": layer_count,
        "sha256": _sha256_bytes(hash_input),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bytes": estimate_cache_size(cache),
    }
    cache_meta_path(session_id).write_text(json.dumps(meta, indent=2))
    return meta


def load_kv_cache_meta(session_id: str) -> Optional[dict]:
    """Return metadata dict if a cache exists, else None."""
    p = cache_meta_path(session_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def load_kv_cache(session_id: str, model) -> list:
    """Restore a cache from disk.

    Returns a list of objects with .keys/.values attributes suitable for
    handing back to mlx-lm's stream_generate(prompt_cache=...).

    Raises FileNotFoundError if no cache exists.
    """
    import mlx.core as mx

    meta = load_kv_cache_meta(session_id)
    if meta is None:
        raise FileNotFoundError(f"no KV cache for session {session_id}")

    out_dir = cache_path_for_session(session_id)
    layers: list = []
    for i in range(meta["layer_count"]):
        path = out_dir / f"layer_{i:03d}.npz"
        if not path.exists():
            break
        data = mx.load(str(path))
        # mx.load returns a dict of arrays when the file is an npz
        k = data["k"] if isinstance(data, dict) else data[0]
        v = data["v"] if isinstance(data, dict) else data[1]
        layers.append(_RestoredLayer(k, v))
    return layers


def delete_kv_cache(session_id: str) -> bool:
    """Remove the cache dir for a session. Returns True if anything was removed."""
    out_dir = cache_path_for_session(session_id)
    if not out_dir.exists():
        return False
    import shutil
    shutil.rmtree(out_dir)
    return True


def list_cached_sessions() -> list[str]:
    """Return session ids with a saved KV cache."""
    if not SESSIONS_DIR.exists():
        return []
    results = []
    for child in SESSIONS_DIR.iterdir():
        if child.is_dir() and (child / "kv_cache" / "meta.json").exists():
            results.append(child.name)
    return sorted(results)


class _RestoredLayer:
    """Minimal cache-layer shim with .keys / .values attributes."""
    __slots__ = ("keys", "values")

    def __init__(self, keys, values):
        self.keys = keys
        self.values = values


def set_sessions_dir(path: str) -> None:
    """Override the sessions directory (tests only)."""
    global SESSIONS_DIR
    SESSIONS_DIR = Path(path).expanduser()
