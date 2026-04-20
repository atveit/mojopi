from std.python import Python, PythonObject

def looks_like_tool_call_attempt(text: String, tool_call_count: Int) raises -> Bool:
    var mod = Python.import_module("agent.parse_retry")
    var result = mod.looks_like_tool_call_attempt(text, tool_call_count)
    return Bool(result)
