# Ports pi-mono ls tool — lists the contents of a directory.
#
# Delegates to ls_helper.py (Python) via Mojo Python interop, which
# uses os.scandir. Entries are returned sorted: directories first,
# then files, both groups alphabetical (case-insensitive).

from std.python import Python, PythonObject
from std.collections import List


struct LsEntry(Copyable, Movable):
    var name: String
    var is_dir: Bool
    var size_bytes: Int64
    var modified_timestamp: Int64

    def __init__(
        out self,
        name: String,
        is_dir: Bool,
        size_bytes: Int64,
        modified_timestamp: Int64,
    ):
        self.name = name.copy()
        self.is_dir = is_dir
        self.size_bytes = size_bytes
        self.modified_timestamp = modified_timestamp


struct LsResult(Copyable, Movable):
    var entries: List[LsEntry]
    var path: String

    def __init__(out self, entries: List[LsEntry], path: String):
        self.entries = entries.copy()
        self.path = path.copy()


def ls_directory(
    path: String,
    show_hidden: Bool = False,
) raises -> LsResult:
    """List directory contents.

    - `path`: directory to list.
    - `show_hidden`: if True, include entries whose names begin with ".".

    Returns an LsResult whose entries are sorted: directories first,
    then files, both groups ordered alphabetically (case-insensitive).
    """
    var helper = Python.import_module("coding_agent.tools.ls_helper")

    var py_result = helper.run_ls(path, show_hidden)

    var py_entries = py_result["entries"]
    var result_path = String(py_result["path"])

    var entries = List[LsEntry]()
    var n = len(py_entries)
    for i in range(n):
        var e = py_entries[i]
        var name = String(e["name"])
        var is_dir = Bool(e["is_dir"])
        var size = Int64(Int(py=e["size"]))
        var mtime = Int64(Int(py=e["mtime"]))
        entries.append(LsEntry(name, is_dir, size, mtime))

    return LsResult(entries^, result_path)
