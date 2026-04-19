from std.python import Python, PythonObject

def fire_event(event_type: String, data_json: String = String("{}")) raises:
    var mod = Python.import_module("coding_agent.extensions.events")
    var json = Python.import_module("json")
    var data = json.loads(data_json)
    mod.fire_event(event_type, data)

def on_event(event_type: String, handler: PythonObject) raises:
    var mod = Python.import_module("coding_agent.extensions.events")
    mod.on(event_type, handler)

def clear_event_handlers() raises:
    var mod = Python.import_module("coding_agent.extensions.events")
    mod.clear_event_handlers()
