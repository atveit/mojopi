from std.python import Python, PythonObject

def new_session_id() raises -> String:
    var mod = Python.import_module("agent.session_manager")
    var result = mod.new_session_id()
    return String(result)

def session_exists(session_id: String) raises -> Bool:
    var mod = Python.import_module("agent.session_manager")
    var result = mod.session_exists(session_id)
    return Bool(result)

def save_turn_message(session_id: String, role: String, content: String,
                      tool_call_id: String = String(""), tool_name: String = String("")) raises:
    var mod = Python.import_module("agent.session_manager")
    var entry = mod.HistoryDict(role, content, tool_call_id, tool_name)
    mod.save_turn(session_id, entry)

def session_message_count(session_id: String) raises -> Int:
    var mod = Python.import_module("agent.session_manager")
    var result = mod.session_message_count(session_id)
    return Int(py=result)
