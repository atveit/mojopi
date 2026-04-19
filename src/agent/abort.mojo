from std.python import Python

def request_abort() raises:
    """Signal abort. Thread-safe — calls Python abort.request_abort()."""
    var mod = Python.import_module("agent.abort")
    _ = mod.request_abort()

def clear_abort() raises:
    """Clear the abort flag. Call at the start of each new user turn."""
    var mod = Python.import_module("agent.abort")
    _ = mod.clear_abort()

def is_aborted() raises -> Bool:
    """Return True if abort has been requested. Non-blocking."""
    var mod = Python.import_module("agent.abort")
    var result = mod.is_aborted()
    return Bool(result)
