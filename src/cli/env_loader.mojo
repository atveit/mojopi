from std.python import Python, PythonObject

def load_dotenv_and_export() raises -> Int:
    """Load .env files; return count of newly-set vars."""
    var mod = Python.import_module("cli.env_loader")
    var builtins = Python.import_module("builtins")
    var result = mod.load_dotenv()
    return Int(py=builtins.len(result))

def env_string(key: String, default_value: String = String("")) raises -> String:
    var os_mod = Python.import_module("os")
    var val = os_mod.environ.get(key, default_value)
    return String(val)
