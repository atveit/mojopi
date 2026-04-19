# Ports pi-mono grep tool — searches files for a regex pattern.
#
# Delegates to grep_helper.py (Python) via Mojo Python interop, which
# tries ripgrep (rg) first and falls back to system grep.

from std.python import Python, PythonObject
from std.collections import List


struct GrepMatch(Copyable, Movable):
    var file_path: String
    var line_number: Int
    var line: String

    def __init__(out self, file_path: String, line_number: Int, line: String):
        self.file_path = file_path.copy()
        self.line_number = line_number
        self.line = line.copy()


struct GrepResult(Copyable, Movable):
    var matches: List[GrepMatch]
    var truncated: Bool
    var total_matches: Int

    def __init__(
        out self,
        matches: List[GrepMatch],
        truncated: Bool,
        total_matches: Int,
    ):
        self.matches = matches.copy()
        self.truncated = truncated
        self.total_matches = total_matches


def grep_text(
    pattern: String,
    path: String,
    include: String = "",
    max_matches: Int = 100,
    case_insensitive: Bool = False,
) raises -> GrepResult:
    """Search for pattern in path using ripgrep (rg) if available, else grep.

    - `pattern`: regular expression to search for.
    - `path`: file or directory to search.
    - `include`: optional glob filter, e.g. "*.py" (empty = all files).
    - `max_matches`: maximum number of matches to return (default 100).
    - `case_insensitive`: if True, search ignores case.

    Returns a GrepResult with up to max_matches GrepMatch entries.
    """
    var helper = Python.import_module("coding_agent.tools.grep_helper")

    var py_result = helper.run_grep(
        pattern,
        path,
        include,
        max_matches,
        case_insensitive,
    )

    var py_matches = py_result["matches"]
    var truncated = Bool(py_result["truncated"])
    var total = Int(py=py_result["total"])

    var matches = List[GrepMatch]()
    var n = len(py_matches)
    for i in range(n):
        var m = py_matches[i]
        var file_path = String(m["file"])
        var line_number = Int(py=m["line"])
        var line_text = String(m["text"])
        matches.append(GrepMatch(file_path, line_number, line_text))

    return GrepResult(matches^, truncated, total)
