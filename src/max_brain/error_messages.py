"""Translate common MLX/MAX/HF errors into short actionable messages."""
from __future__ import annotations
from typing import Optional


_MAPPINGS = [
    # (substring or pattern, friendly message)
    ("pydantic_core._pydantic_core.ValidationError",
     "Could not load model on the configured device. If you're on arm64, "
     "verify MAXModelConfig uses DeviceSpec.cpu(). See docs/MODEL_VERIFICATION.md."),
    ("external memory not supported on Apple GPU",
     "MAX's Apple GPU sampling kernel is blocked on arm64. mojopi uses MLX Metal "
     "instead; check src/max_brain/mlx_backend.py is being used."),
    ("Connection error",
     "Network failure while fetching model weights. Check internet and try again."),
    ("HFValidationError",
     "Invalid HuggingFace model repo id. Format: <user>/<model-name>."),
    ("No space left on device",
     "Disk full — model weights need several GB. Free some space and retry."),
    ("OSError: [Errno 2]",
     "File not found. If this is a model repo, check the name and your HF cache "
     "(~/.cache/huggingface/hub/)."),
    ("CUDA",
     "CUDA-related failure. On Apple Silicon, use the MLX Metal backend "
     "(automatic on arm64)."),
    ("topk",
     "MAX topk sampling hit a kernel limit. This is a known MAX 26.2 issue on "
     "Apple GPU; mojopi falls back to CPU automatically."),
]


def friendly_mlx_error(exc: BaseException) -> str:
    """Translate an exception into a short, user-facing message.

    Falls through to a truncated repr of the exception if nothing matches.
    Never raises; safe for use inside `except:` blocks.
    """
    try:
        msg = str(exc)
    except Exception:
        msg = repr(exc)
    type_name = type(exc).__name__
    combined = f"{type_name}: {msg}"
    for needle, friendly in _MAPPINGS:
        if needle in combined:
            return friendly + f"  (original: {type_name})"
    # Fallback: first line of the error, clipped
    first_line = msg.splitlines()[0] if msg else type_name
    if len(first_line) > 200:
        first_line = first_line[:197] + "..."
    return f"Model failed: {first_line}  (type: {type_name})"


def hint_for_cold_start(model_repo: str) -> str:
    """Return a user-facing hint when cold-start is slow."""
    return (
        f"First run of {model_repo} downloads + warms the model — "
        "typical cold start is 30–90 s on M-series. Subsequent runs are cached."
    )


def list_known_errors() -> list[str]:
    """Return the list of substring triggers this module knows about."""
    return [needle for needle, _ in _MAPPINGS]
