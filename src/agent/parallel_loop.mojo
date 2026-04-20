from std.python import Python, PythonObject

def is_read_only_tool_name(name: String) raises -> Bool:
    var mod = Python.import_module("agent.parallel_loop")
    return Bool(mod._is_read_only(name))
