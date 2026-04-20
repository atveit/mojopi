from std.python import Python, PythonObject

def turboquant_available() raises -> Bool:
    try:
        var _ = Python.import_module("max_brain.turboquant")
        return True
    except:
        return False
