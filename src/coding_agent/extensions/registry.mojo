from std.python import Python, PythonObject
from std.collections import List

def get_registered_tool_names() raises -> List[String]:
    var mod = Python.import_module("coding_agent.extensions.registry")
    var tools = mod.get_registered_tools()
    var keys = Python.evaluate("list")(tools.keys())
    var names = List[String]()
    for i in range(Int(py=Python.evaluate("len")(keys))):
        names.append(String(keys[i]))
    return names^

def dispatch_registered_tool(name: String, arguments_json: String) raises -> String:
    var mod = Python.import_module("coding_agent.extensions.registry")
    var result = mod.dispatch_registered_tool(name, arguments_json)
    return String(result)

def clear_registry() raises:
    var mod = Python.import_module("coding_agent.extensions.registry")
    mod.clear_registry()
