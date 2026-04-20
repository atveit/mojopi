from std.python import Python, PythonObject

def search_sessions_text(query: String, max_results: Int = 50) raises -> String:
    var mod = Python.import_module("cli.search")
    var hits = mod.search_sessions(query, max_results)
    return String(mod.format_results(hits, query))

def search_hit_count(query: String) raises -> Int:
    var mod = Python.import_module("cli.search")
    var builtins = Python.import_module("builtins")
    var hits = mod.search_sessions(query)
    return Int(py=builtins.len(hits))
