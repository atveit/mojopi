from std.python import Python, PythonObject

def wrap_python_tool(name: String, fn: PythonObject, description: String = String(""), schema_json: String = String("{}")) raises:
    """Register a Python callable as a tool in the extension registry."""
    var mod = Python.import_module("coding_agent.extensions.custom_tool")
    _ = mod.wrap_python_tool(name, fn, description, schema_json)

def dispatch_custom_tool(name: String, arguments_json: String) raises -> String:
    """Dispatch a registered Python tool by name. Returns result string."""
    var reg = Python.import_module("coding_agent.extensions.registry")
    var result = reg.dispatch_registered_tool(name, arguments_json)
    return String(result)
