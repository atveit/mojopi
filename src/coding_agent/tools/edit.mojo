# Ports pi-mono/packages/coding-agent/src/core/tools/edit.ts — C2 subset.
#
# Scope for C2: targeted single-occurrence string replacement in a file.
# Fails on 0 matches ("not found") or >1 matches ("ambiguous").
# Delegates to edit_helper.py via Python interop.

from std.python import Python, PythonObject


struct EditResult(Copyable, Movable):
    var success: Bool
    var error: String  # empty string = no error
    var match_count: Int

    def __init__(out self, success: Bool, error: String, match_count: Int):
        self.success = success
        self.error = error.copy()
        self.match_count = match_count


def apply_edit(
    file_path: String,
    old_string: String,
    new_string: String,
) raises -> EditResult:
    """Apply a targeted string replacement in a file.

    Returns an EditResult with success, error (empty on success), and
    match_count.  Raises on unexpected Python-level errors.
    """
    var mod = Python.import_module("coding_agent.tools.edit_helper")
    var result = mod.apply_edit(file_path, old_string, new_string)
    var err_py = result["error"]
    var err_str = String("")
    var builtins = Python.import_module("builtins")
    var is_none_fn = Python.evaluate("lambda x: x is None")
    if not Bool(is_none_fn(err_py).__bool__()):
        err_str = String(err_py)
    return EditResult(
        Bool(result["success"]),
        err_str,
        Int(py=result["match_count"]),
    )
