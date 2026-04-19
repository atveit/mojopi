from std.python import Python, PythonObject
from std.collections import List

def is_structured_output_available() raises -> Bool:
    var mod = Python.import_module("agent.structured_output")
    var result = mod.is_structured_output_available()
    return Bool(result)

def regex_extract_tool_calls(text: String) raises -> List[String]:
    """Extract tool call JSON strings from free-form text."""
    var mod = Python.import_module("agent.structured_output")
    var calls = mod._regex_extract_tool_calls(text)
    var json_mod = Python.import_module("json")
    var results = List[String]()
    var n = Int(py=Python.evaluate("len")(calls))
    for i in range(n):
        var call = calls[i]
        var call_str = String(json_mod.dumps(call))
        results.append(call_str)
    return results^
