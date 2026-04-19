"""MAX inference pipeline — Python-side adapter for Mojo callers.

MAX is Python-first in 2026; the Mojo `max.engine` API is deprecated. This
module wraps max.pipelines and max.kv_cache behind a minimal interface the
Mojo side imports via `from python import Python`.
"""
from __future__ import annotations
from typing import Any


def get_max_version() -> str:
    """Return the installed MAX version string. Used by the C1 smoke gate.

    The MAX Python package does not expose `__version__` consistently across
    releases — in some builds it's `max.version.__version__`, in others it
    lives only in the conda metadata. Probe several locations and fall back
    to importlib.metadata before declaring it unknown.
    """
    try:
        import max
    except ModuleNotFoundError:
        return "max-not-installed"

    # 1. Direct attributes on the `max` module.
    for attr in ("__version__", "VERSION", "version"):
        v = getattr(max, attr, None)
        if v is not None and not callable(v) and not hasattr(v, "__version__"):
            return str(v)

    # 2. Nested `max.version.__version__` (seen in some MAX builds).
    try:
        from max import version as _v_mod
        inner = getattr(_v_mod, "__version__", None)
        if inner:
            return str(inner)
    except Exception:
        pass

    # 3. Conda / pip package metadata, under any of the known package names.
    try:
        from importlib.metadata import version, PackageNotFoundError
        for pkg in ("max", "max-pipelines", "modular", "max-engine"):
            try:
                return version(pkg)
            except PackageNotFoundError:
                continue
    except Exception:
        pass

    return "installed (version unknown)"


def build_pipeline(model_repo: str, max_length: int = 8192) -> dict[str, Any]:
    """Construct a TextGenerationPipeline config.

    For C2, this only needs to report that the pipeline *can be constructed* —
    it does not yet execute generation. Returns a dict describing the config
    so the Mojo side can log/inspect it without depending on MAX internals.
    """
    from max.pipelines import PipelineConfig, TextGenerationPipeline  # lazy
    cfg = PipelineConfig(model=model_repo, max_length=max_length)
    pipeline = TextGenerationPipeline(cfg)
    return {
        "model": model_repo,
        "max_length": max_length,
        "pipeline_class": type(pipeline).__name__,
    }


def stream_tokens(pipeline_handle: Any, prompt: str):
    """Yield decoded token strings from a pipeline. Stub for C3.

    C3 requires streaming tokens back to the Mojo caller. This function is
    the lowest-level bridge. Implemented in C3 once build_pipeline is solid.
    """
    raise NotImplementedError("streaming is a C3 deliverable")
