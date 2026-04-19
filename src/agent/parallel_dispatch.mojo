from std.python import Python, PythonObject
from std.collections import List
from agent.types import ParsedToolCall

def is_read_only_tool(name: String) raises -> Bool:
    var mod = Python.import_module("agent.parallel_dispatch")
    var result = mod._is_read_only(name)
    return Bool(result)

def dispatch_parallel_results_count(results: PythonObject) raises -> Int:
    var builtins = Python.import_module("builtins")
    return Int(py=builtins.len(results))

def get_result_at(results: PythonObject, idx: Int) raises -> String:
    var r = results[idx]
    return String(r.result)

def get_result_error_at(results: PythonObject, idx: Int) raises -> String:
    var r = results[idx]
    return String(r.error)

def result_is_success(results: PythonObject, idx: Int) raises -> Bool:
    var r = results[idx]
    return Bool(r.success)
