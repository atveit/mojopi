from std.python import Python, PythonObject

def cache_exists_for_session(session_id: String) raises -> Bool:
    var mod = Python.import_module("max_brain.kv_cache")
    var meta = mod.load_kv_cache_meta(session_id)
    var is_none = Python.evaluate("lambda x: x is None")
    return not Bool(is_none(meta))

def delete_kv_cache(session_id: String) raises -> Bool:
    var mod = Python.import_module("max_brain.kv_cache")
    var result = mod.delete_kv_cache(session_id)
    return Bool(result)

def cache_size_bytes(session_id: String) raises -> Int:
    var mod = Python.import_module("max_brain.kv_cache")
    var meta = mod.load_kv_cache_meta(session_id)
    var is_none = Python.evaluate("lambda x: x is None")
    if Bool(is_none(meta)):
        return 0
    return Int(py=meta.get("bytes", 0))
