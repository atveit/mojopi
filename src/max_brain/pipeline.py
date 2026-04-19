"""MAX inference pipeline — Python-side adapter for Mojo callers.

MAX is Python-first in 2026; the Mojo `max.engine` API is deprecated. This
module wraps max.pipelines and max.kv_cache behind a minimal interface the
Mojo side imports via `from python import Python`.
"""
from __future__ import annotations
from typing import Any


def get_max_version() -> str:
    """Return the installed MAX version string. Used by the C1 smoke gate."""
    # Import inside the function so the module itself is importable even when
    # MAX is not installed (supports environments running only Python tests).
    try:
        import max
        return getattr(max, "__version__", "unknown")
    except ModuleNotFoundError:
        return "max-not-installed"


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
