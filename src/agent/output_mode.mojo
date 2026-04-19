from std.python import Python, PythonObject

def emit_token(text: String, mode: String = String("print")) raises:
    var mod = Python.import_module("agent.output_mode")
    mod.emit_token(text, mode)

def emit_tool_call(name: String, arguments_json: String, mode: String = String("print")) raises:
    var mod = Python.import_module("agent.output_mode")
    var json = Python.import_module("json")
    var args = json.loads(arguments_json)
    mod.emit_tool_call(name, args, mode)

def emit_answer(text: String, mode: String = String("print")) raises:
    var mod = Python.import_module("agent.output_mode")
    mod.emit_answer(text, mode)

def emit_error(message: String, mode: String = String("print")) raises:
    var mod = Python.import_module("agent.output_mode")
    mod.emit_error(message, mode)

def is_valid_mode(mode: String) raises -> Bool:
    var mod = Python.import_module("agent.output_mode")
    var result = mod.is_valid_mode(mode)
    return Bool(result)
