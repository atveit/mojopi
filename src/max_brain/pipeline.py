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


def stream_tokens(
    prompt: str,
    model: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 64,
):
    """Yield stdout chunks from `max generate` as they arrive.

    C3 one-shot path: shells out to the bundled `max` CLI which handles
    model download/load/compile/generate/teardown per invocation. Slow
    (graph compile every call) but the simplest path that actually works
    in MAX 26.2. Interactive use (W2) will move to an embedded
    TextGenerationPipeline that amortizes load across turns.

    The `max` CLI logs are mixed into stdout; the Mojo caller is
    responsible for filtering or displaying as-is. C3's demo gate accepts
    log-adjacent output.
    """
    import subprocess

    # MAX 26.2 topk kernel hits an "external memory not supported on Apple GPU"
    # constraint during sampling graph compile. Forcing CPU avoids that. On
    # Linux + CUDA, remove `--devices cpu` (R2 will auto-detect).
    cmd = [
        "max", "generate",
        "--model-path", model,
        "--prompt", prompt,
        "--max-new-tokens", str(max_new_tokens),
        "--devices", "cpu",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            yield line
    finally:
        rc = proc.wait()
        if rc != 0:
            yield f"\n[max generate exited with code {rc}]\n"
