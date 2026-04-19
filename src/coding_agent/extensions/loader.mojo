from std.python import Python

def load_all_extensions(extra: String = String("")) raises -> Int:
    var mod = Python.import_module("coding_agent.extensions.loader")
    var count = mod.load_all_extensions(extra)
    return Int(py=count)

def load_extensions_dir(directory: String) raises -> Int:
    var mod = Python.import_module("coding_agent.extensions.loader")
    var count = mod.load_extensions_dir(directory)
    return Int(py=count)
