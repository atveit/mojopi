# Ports pi-mono/packages/coding-agent/src/core/tools/write.ts — C2 subset.
#
# Scope for C2: write content to a file, optionally creating parent
# directories.  Overwrites any existing content.  Delegates mkdir and file
# I/O to Python's pathlib (Mojo pathlib may not expose mkdir).

from std.python import Python


struct WriteResult(Copyable, Movable):
    var success: Bool
    var bytes_written: Int
    var error: String

    def __init__(out self, success: Bool, bytes_written: Int, error: String):
        self.success = success
        self.bytes_written = bytes_written
        self.error = error.copy()


def write_file(
    file_path: String,
    content: String,
    create_parents: Bool = True,
) raises -> WriteResult:
    """Write content to file_path, optionally creating parent directories.

    Overwrites existing content.  Returns a WriteResult with the number of
    bytes written (UTF-8 encoded length of content).
    """
    var py = Python.import_module("pathlib")
    var p = py.Path(file_path)
    if create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return WriteResult(True, len(content), String(""))
