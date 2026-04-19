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
) raises:
    """C3 one-shot driver: stream `max generate` stdout to stdout.

    Calls max_brain.pipeline.stream_tokens, which shells out to the bundled
    MAX CLI. Each yielded chunk is a line of subprocess stdout (MAX logs
    and generated text mixed). We write through Python's sys.stdout so
    each chunk flushes immediately, giving the user the token-by-line
    streaming feel the C3 gate calls for.
    """
    var mod = Python.import_module("max_brain.pipeline")
    var sys_mod = Python.import_module("sys")
    var gen = mod.stream_tokens(prompt, model, max_new_tokens)
    for chunk in gen:
        # `chunk` already ends in \n from the subprocess. Using
        # sys.stdout.write avoids print's extra newline + gives us flush.
        _ = sys_mod.stdout.write(chunk)
        _ = sys_mod.stdout.flush()


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
