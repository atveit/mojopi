from std.python import Python, PythonObject

def generate_threaded(prompt: String, model_repo: String = String("modularai/Llama-3.1-8B-Instruct-GGUF"), max_new_tokens: Int = 64) raises -> String:
    """Generate via dedicated MAX thread (isolates GIL contention)."""
    var mod = Python.import_module("max_brain.threaded_pipeline")
    var result = mod.generate_threaded(prompt, model_repo, max_new_tokens)
    return String(result)

def get_pool_metrics() raises -> String:
    """Return pool metrics as JSON string."""
    var mod = Python.import_module("max_brain.threaded_pipeline")
    var json = Python.import_module("json")
    var pool = mod.get_inference_pool()
    var metrics = pool.get_metrics()
    return String(json.dumps(metrics))
