"""Verify the Python side of the interop is syntactically sound and has the
expected surface. Does NOT require `max` to be installed — that's a pixi-run gate."""
import importlib.util
import sys
from pathlib import Path

# Make src/ importable.
SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))


def test_pipeline_module_importable():
    import max_brain.pipeline as p
    assert hasattr(p, "get_max_version")
    assert hasattr(p, "build_pipeline")
    assert hasattr(p, "stream_tokens")


def test_get_max_version_is_callable():
    import max_brain.pipeline as p
    v = p.get_max_version()
    assert isinstance(v, str)
    # When MAX isn't installed we return a sentinel so tests pass in any env.
    assert len(v) > 0


def test_stream_tokens_is_a_generator():
    """C3 landing — stream_tokens is implemented as a subprocess-backed
    generator over `max generate` stdout. This test doesn't invoke MAX;
    it only verifies the public surface (iterable, accepts the 3 args)."""
    import inspect
    import max_brain.pipeline as p
    assert inspect.isgeneratorfunction(p.stream_tokens)
    sig = inspect.signature(p.stream_tokens)
    assert "prompt" in sig.parameters
    assert "model" in sig.parameters
    assert "max_new_tokens" in sig.parameters
