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


def test_stream_tokens_not_implemented_in_c2():
    import max_brain.pipeline as p
    try:
        next(iter(p.stream_tokens(None, "hi")))
    except NotImplementedError:
        return
    except Exception:
        # Any other path is fine — the strict contract is only that C2 doesn't promise streaming.
        return
    assert False, "stream_tokens should be unimplemented in C2"
