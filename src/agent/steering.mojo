from std.python import Python, PythonObject

def push_steering(message: String) raises:
    """Push a steering message into the Python queue. Thread-safe."""
    var mod = Python.import_module("agent.steering")
    _ = mod.push_steering(message)

def poll_steering() raises -> String:
    """Non-blocking poll. Returns the next steering message or empty string if none.

    Call at each turn boundary in the agent loop.
    """
    var mod = Python.import_module("agent.steering")
    var result = mod.poll_steering()
    # Python None -> empty string
    var is_none_fn = Python.evaluate("lambda x: x is None")
    if Bool(is_none_fn(result)):
        return String("")
    return String(result)

def poll_all_steering() raises -> PythonObject:
    """Drain the queue. Returns Python list[str] of all pending messages."""
    var mod = Python.import_module("agent.steering")
    return mod.poll_all_steering()

def clear_steering() raises:
    """Discard all pending steering messages."""
    var mod = Python.import_module("agent.steering")
    _ = mod.clear_steering()

def queue_depth() raises -> Int:
    """Return the number of pending messages."""
    var mod = Python.import_module("agent.steering")
    var n = mod.queue_depth()
    return Int(py=n)
