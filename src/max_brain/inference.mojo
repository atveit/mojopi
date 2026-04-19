# Mojo-side wrapper around max_brain/pipeline.py.
# MAX is Python-first; we go through `from std.python import Python`.
from std.python import Python, PythonObject


def get_max_version() raises -> String:
    """C1 smoke gate: prove Python interop reaches MAX (or reports it's absent)."""
    var mod = Python.import_module("max_brain.pipeline")
    var v = mod.get_max_version()
    return String(v)


def run_one_shot(
    prompt: String,
    model: String,
    max_new_tokens: Int = 64,
) raises -> Int:
    """C3 one-shot driver: stream `max generate` stdout to stdout.

    Delegates the subprocess iteration to Python (max_brain.pipeline.
    run_one_shot). Keeping the loop in Python sidesteps an early
    truncation seen when Mojo iterates a Python generator over this
    specific stream — probably related to the tqdm progress lines the
    MAX CLI emits mid-download. One call, full output.
    """
    var mod = Python.import_module("max_brain.pipeline")
    var rc = mod.run_one_shot(prompt, model, max_new_tokens)
    # Int(py=...) is the current-Mojo form for PythonObject → Int.
    return Int(py=rc)


struct MaxInference(Movable):
    """Kept for API continuity with earlier C2 scaffolding. The actual
    C3 demo driver is `run_one_shot()` above; a full embedded pipeline
    (with persistent model load + token-level streaming through
    TextGenerationPipeline) is a W2 concern."""

    var model_repo: String

    def __init__(out self, model_repo: String) raises:
        self.model_repo = model_repo.copy()

    def describe(self) -> String:
        return String("MaxInference(model=") + self.model_repo + ")"
