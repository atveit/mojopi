"""MAX inference pipeline — Python-side adapter for Mojo callers.

MAX is Python-first in 2026; the Mojo `max.engine` API is deprecated. This
module wraps max.pipelines and max.kv_cache behind a minimal interface the
Mojo side imports via `from python import Python`.
"""
from __future__ import annotations
from typing import Any
import platform

_is_arm64 = platform.machine() == "arm64"

# Module-level pipeline cache: model_repo -> TextGenerationPipeline instance
_pipeline_cache: dict = {}


def _make_pipeline_config(model_repo: str, max_length: int) -> Any:
    """Build a PipelineConfig, pinning to CPU on Apple Silicon.

    MAX 26.2+ changed the API: `model` must be an MAXModelConfig object
    (not a string), and CPU pinning uses DeviceSpec.cpu() in device_specs.
    On Linux + CUDA, device_specs is left empty for auto-detection.
    """
    from max.pipelines import PipelineConfig
    from max.pipelines.lib.config.model_config import MAXModelConfig
    if _is_arm64:
        from max.driver import DeviceSpec
        model_cfg = MAXModelConfig(
            model_path=model_repo,
            max_length=max_length,
            device_specs=[DeviceSpec.cpu()],
        )
    else:
        model_cfg = MAXModelConfig(model_path=model_repo, max_length=max_length)
    return PipelineConfig(model=model_cfg)


def get_or_create_pipeline(
    model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_length: int = 8192,
) -> object:
    """Load TextGenerationPipeline once; cache by model_repo.

    IMPORTANT: On Apple Silicon (arm64), GPU sampling is broken in MAX 26.2
    due to a topk kernel 'external memory' constraint. Must use CPU.
    Set devices='cpu' in PipelineConfig on arm64.

    Returns the cached pipeline instance. Raises on import or init failure
    so callers can fall back gracefully.
    """
    if model_repo in _pipeline_cache:
        return _pipeline_cache[model_repo]

    from max.pipelines import TextGenerationPipeline
    cfg = _make_pipeline_config(model_repo, max_length)
    pipeline = TextGenerationPipeline(cfg)

    available = [m for m in dir(pipeline) if not m.startswith('_')]
    print(f"[pipeline] methods: {available}")

    _pipeline_cache[model_repo] = pipeline
    return pipeline


def generate_embedded(
    prompt: str,
    model_repo: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 64,
) -> str:
    """Generate text using the cached pipeline (no subprocess).

    Drives iteration in Python (do NOT iterate a Python generator from Mojo —
    it truncates early around chunk 16). Returns the generated text as a string.

    Falls back to run_one_shot() if the embedded pipeline raises.
    """
    try:
        pipeline = get_or_create_pipeline(model_repo)
    except Exception as exc:
        print(f"[pipeline] get_or_create_pipeline failed ({exc}); falling back to subprocess")
        run_one_shot(prompt, model_repo, max_new_tokens)
        return ""

    # Try API patterns in order of likelihood for MAX 26.2 / max-pipelines.
    # Pattern 1: streaming next() API
    if hasattr(pipeline, "next"):
        try:
            tokens: list[str] = []
            for token in pipeline.next(prompt):
                tokens.append(str(token))
            return "".join(tokens)
        except Exception as exc:
            print(f"[pipeline] pipeline.next() failed ({exc}); trying next pattern")

    # Pattern 2: batch generate() API
    if hasattr(pipeline, "generate"):
        try:
            result = pipeline.generate(prompt, max_new_tokens=max_new_tokens)
            return str(result)
        except Exception as exc:
            print(f"[pipeline] pipeline.generate() failed ({exc}); trying next pattern")

    # Pattern 3: callable API
    try:
        tokens: list[str] = []
        for token in pipeline(prompt):
            tokens.append(str(token))
        return "".join(tokens)
    except Exception as exc:
        print(f"[pipeline] pipeline(...) callable failed ({exc}); falling back to subprocess")

    # Final fallback: subprocess
    print("[pipeline] all embedded API patterns failed; falling back to run_one_shot()")
    run_one_shot(prompt, model_repo, max_new_tokens)
    return ""


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
    from max.pipelines import TextGenerationPipeline  # lazy
    cfg = _make_pipeline_config(model_repo, max_length)
    pipeline = TextGenerationPipeline(cfg)
    return {
        "model": model_repo,
        "max_length": max_length,
        "pipeline_class": type(pipeline).__name__,
    }


def _build_max_generate_cmd(model: str, prompt: str, max_new_tokens: int) -> list[str]:
    """Shared command builder. MAX 26.2 topk kernel hits an
    "external memory not supported on Apple GPU" constraint during
    sampling graph compile. Forcing CPU avoids that. On Linux + CUDA,
    remove --devices cpu (R2 will auto-detect).
    """
    return [
        "max", "generate",
        "--model-path", model,
        "--prompt", prompt,
        "--max-new-tokens", str(max_new_tokens),
        "--devices", "cpu",
    ]


def stream_tokens(
    prompt: str,
    model: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 64,
):
    """Yield stdout chunks from `max generate` as they arrive.

    A generator is the right shape for downstream iteration in Python,
    but Mojo's PythonObject iteration truncates early on this stream
    (see run_one_shot() for the fix). Python-side callers can still
    use this directly if they want chunk-level control.
    """
    import subprocess

    proc = subprocess.Popen(
        _build_max_generate_cmd(model, prompt, max_new_tokens),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            yield line
    finally:
        rc = proc.wait()
        if rc != 0:
            yield f"\n[max generate exited with code {rc}]\n"


def run_one_shot(
    prompt: str,
    model: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    max_new_tokens: int = 64,
) -> int:
    """Run `max generate` once and stream its output to stdout, returning
    the subprocess exit code.

    This is the Mojo-facing entrypoint. Keeping the iteration in Python
    sidesteps a PythonObject-iteration truncation the Mojo side hits when
    looping a generator directly — the Mojo caller just awaits this single
    call and the full output lands on stdout as the subprocess produces it.
    """
    import subprocess
    import sys

    proc = subprocess.Popen(
        _build_max_generate_cmd(model, prompt, max_new_tokens),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
    finally:
        rc = proc.wait()
    if rc != 0:
        sys.stdout.write(f"\n[max generate exited with code {rc}]\n")
        sys.stdout.flush()
    return rc
