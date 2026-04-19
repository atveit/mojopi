from std.python import Python, PythonObject

def register_before_tool_call(hook: PythonObject, name: String = "") raises:
    """Register a Python callable as a before_tool_call hook."""
    var mod = Python.import_module("agent.hooks")
    _ = mod.register_before_tool_call(hook, name)

def register_after_tool_call(hook: PythonObject, name: String = "") raises:
    """Register a Python callable as an after_tool_call hook."""
    var mod = Python.import_module("agent.hooks")
    _ = mod.register_after_tool_call(hook, name)

def clear_hooks() raises:
    """Clear all registered hooks."""
    var mod = Python.import_module("agent.hooks")
    _ = mod.clear_hooks()

def run_before_hooks(tool_name: String, arguments_json: String) raises -> String:
    """Run all before hooks. Returns (possibly modified) arguments_json."""
    var mod = Python.import_module("agent.hooks")
    var result = mod.run_before_hooks(tool_name, arguments_json)
    return String(result)

def run_after_hooks(tool_name: String, arguments_json: String, result: String) raises -> String:
    """Run all after hooks. Returns (possibly modified) result."""
    var mod = Python.import_module("agent.hooks")
    var r = mod.run_after_hooks(tool_name, arguments_json, result)
    return String(r)
