# Mojo-side wrapper around max_brain/pipeline.py.
# MAX is Python-first; we go through `from python import Python`.
from python import Python, PythonObject


def get_max_version() -> String:
    """C1 smoke gate: prove Python interop reaches MAX (or reports it's absent)."""
    var mod = Python.import_module("max_brain.pipeline")
    var v = mod.get_max_version()
    return String(v)


struct MaxInference(Movable):
    var _config: PythonObject    # the dict returned by build_pipeline
    var model_repo: String

    def __init__(out self, model_repo: String):
        self.model_repo = model_repo
        var mod = Python.import_module("max_brain.pipeline")
        self._config = mod.build_pipeline(model_repo)

    def describe(self) -> String:
        """Return a short human-readable summary of the loaded pipeline."""
        return String(self._config)
