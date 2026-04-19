# Ports pi-mono find tool — walks a directory tree for matching paths.
#
# Delegates to find_helper.py (Python) via Mojo Python interop, which
# uses pathlib.Path.rglob for portability.

from std.python import Python, PythonObject
from std.collections import List


struct FindResult(Copyable, Movable):
    var paths: List[String]
    var truncated: Bool
    var total_found: Int

    def __init__(
        out self,
        paths: List[String],
        truncated: Bool,
        total_found: Int,
    ):
        self.paths = paths.copy()
        self.truncated = truncated
        self.total_found = total_found


def find_files(
    directory: String,
    pattern: String = "*",
    file_type: String = "",
    max_results: Int = 100,
    exclude_dirs: List[String] = List[String](),
) raises -> FindResult:
    """Find files matching pattern under directory.

    - `directory`: root directory to search under.
    - `pattern`: glob pattern to match, e.g. "*.py" (default "*" = everything).
    - `file_type`: "" = both, "f" = files only, "d" = directories only.
    - `max_results`: cap on returned paths (default 100).
    - `exclude_dirs`: directory names to skip (default: .git, node_modules, …).

    Returns a FindResult with matching paths.
    """
    var helper = Python.import_module("coding_agent.tools.find_helper")

    # Build Python list for exclude_dirs
    var py_exclude = Python.list()
    for i in range(len(exclude_dirs)):
        _ = py_exclude.append(exclude_dirs[i])

    var py_result = helper.run_find(
        directory,
        pattern,
        file_type,
        max_results,
        py_exclude,
    )

    var py_paths = py_result["paths"]
    var truncated = Bool(py_result["truncated"])
    var total = Int(py=py_result["total"])

    var paths = List[String]()
    var n = len(py_paths)
    for i in range(n):
        paths.append(String(py_paths[i]))

    return FindResult(paths^, truncated, total)
