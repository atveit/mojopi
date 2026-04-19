from std.python import Python, PythonObject
from std.collections import List


def estimate_history_tokens(history_json: String) raises -> Int:
    """Estimate token count for a JSON-encoded history list.
    Calls Python compactor.estimate_history_tokens via json.loads + compactor call.
    """
    var py_json = Python.import_module("json")
    var mod = Python.import_module("coding_agent.compaction.compactor")
    var py_history = py_json.loads(history_json)
    var n = mod.estimate_history_tokens(py_history)
    return Int(py=n)


def should_compact(history_json: String, max_tokens: Int = 8192) raises -> Bool:
    """Return True if history should be compacted.
    Calls Python compactor.should_compact.
    """
    var py_json = Python.import_module("json")
    var mod = Python.import_module("coding_agent.compaction.compactor")
    var py_history = py_json.loads(history_json)
    var result = mod.should_compact(py_history, max_tokens)
    return Bool(result)


def compact_history(
    history_json: String,
    model: String = "modularai/Llama-3.1-8B-Instruct-GGUF",
    keep_last_n: Int = 4,
) raises -> PythonObject:
    """Compact old history entries. Returns Python tuple (new_history_list, summary_str).
    The caller should json.dumps the new_history_list to get an updated history_json.
    """
    var py_json = Python.import_module("json")
    var mod = Python.import_module("coding_agent.compaction.compactor")
    var py_history = py_json.loads(history_json)
    return mod.compact_history(py_history, model, keep_last_n)
