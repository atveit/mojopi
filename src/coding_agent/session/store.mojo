# Mojo wrapper that delegates all session I/O to the Python store module.
#
# Follows the PLAN §0 empirical corrections:
#   C1 — std.* prefix required for all stdlib imports
#   C1 — def does NOT implicitly raise; explicit `raises` on every def that
#        calls Python.import_module or any other raising operation
#   C1 — def params are immutable refs; String fields use .copy() in constructors
#   C8 — Mojo print() has no file= kwarg
#
# Usage from Mojo:
#
#   var entries = read_session(String("/path/to/session.jsonl"))
#   var leaves  = get_leaf_branches(entries)
#   var path    = resolve_path(entries, String("leaf-id"))

from std.python import Python, PythonObject


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _store_module() raises -> PythonObject:
    """Import and return the Python coding_agent.session.store module.

    The `coding_agent` package is on PYTHONPATH (src/) — same layout used by
    all other Python interop in this repo.

    Raises if the import fails (e.g. PYTHONPATH not set correctly).
    """
    return Python.import_module("coding_agent.session.store")


# ---------------------------------------------------------------------------
# Public API — mirrors the Python store.py surface
# ---------------------------------------------------------------------------


def read_session(path: String) raises -> PythonObject:
    """Call Python store.read_session; returns a Python list of dicts.

    Args:
        path: Filesystem path to the .jsonl session file.

    Returns:
        A PythonObject wrapping a Python list[dict].  Iterate with
        `for entry in result` or index with `result[i]`.

    Raises:
        If the Python import fails, or if the underlying Python function
        raises (file not found, invalid JSON, etc.).
    """
    var store = _store_module()
    return store.read_session(path)


def write_session(path: String, entries: PythonObject) raises:
    """Call Python store.write_session.

    Serialises *entries* (a Python list of dicts) to a JSONL file at *path*.

    Args:
        path:    Destination filesystem path.
        entries: PythonObject wrapping a Python list[dict].

    Raises:
        If the Python import fails, or if the underlying write fails
        (e.g. permission denied, parent directory missing).
    """
    var store = _store_module()
    _ = store.write_session(path, entries)


def get_leaf_branches(entries: PythonObject) raises -> PythonObject:
    """Call Python store.get_leaf_branches; returns a Python list of id strings.

    Args:
        entries: PythonObject wrapping a Python list[dict] from read_session().

    Returns:
        A PythonObject wrapping a Python list[str] of leaf entry ids.
    """
    var store = _store_module()
    return store.get_leaf_branches(entries)


def resolve_path(entries: PythonObject, leaf_id: String) raises -> PythonObject:
    """Call Python store.resolve_path; returns a Python list of entry dicts.

    Walks from *leaf_id* up the parent chain and returns the path in
    root → leaf order.

    Args:
        entries: PythonObject wrapping the full session entry list.
        leaf_id: The id of the leaf entry defining the branch.

    Returns:
        A PythonObject wrapping a Python list[dict], ordered root → leaf.

    Raises:
        If the Python import fails, or if the Python function raises
        (unknown id, cycle detected, broken parent chain).
    """
    var store = _store_module()
    return store.resolve_path(entries, leaf_id)
