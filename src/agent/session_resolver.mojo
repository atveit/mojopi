from std.python import Python, PythonObject

def resolve_session_id(id_or_prefix: String) raises -> String:
    var mod = Python.import_module("agent.session_resolver")
    var result = mod.resolve_session_id(id_or_prefix)
    return String(result)

def get_latest_session_id() raises -> String:
    var mod = Python.import_module("agent.session_resolver")
    var result = mod.get_latest_session_id()
    var is_none = Python.evaluate("lambda x: x is None")
    if Bool(is_none(result)):
        return String("")
    return String(result)

def session_count() raises -> Int:
    var mod = Python.import_module("agent.session_resolver")
    var builtins = Python.import_module("builtins")
    var sessions = mod.list_all_sessions()
    return Int(py=builtins.len(sessions))
