from std.python import Python, PythonObject

def generate_speculative(prompt: String, main_repo: String, draft_repo: String = String("mlx-community/Llama-3.2-1B-Instruct-4bit"), max_new_tokens: Int = 512) raises -> String:
    """Generate using speculative decoding via MLX."""
    var mod = Python.import_module("max_brain.speculative")
    var result = mod.generate_speculative(prompt, main_repo, draft_repo, max_new_tokens)
    return String(result)

def is_speculative_available() raises -> Bool:
    var mod = Python.import_module("max_brain.speculative")
    var result = mod.is_available()
    return Bool(result)
