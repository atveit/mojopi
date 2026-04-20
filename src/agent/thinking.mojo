from std.python import Python, PythonObject

def strip_thinking_text(text: String) raises -> String:
    var mod = Python.import_module("agent.thinking")
    var result = mod.strip_thinking_text(text)
    return String(result)

def has_thinking_block(text: String) raises -> Bool:
    var mod = Python.import_module("agent.thinking")
    return Bool(mod.has_thinking_block(text))
