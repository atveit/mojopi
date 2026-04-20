from std.python import Python, PythonObject


def estimate_history_tokens_str(history_text: String) raises -> Int:
    """Approximate token count for a single text blob."""
    var mod = Python.import_module("coding_agent.compaction.compactor")
    var result = mod.estimate_tokens(history_text)
    return Int(py=result)


def should_auto_compact_size(total_tokens: Int, max_tokens: Int = 8192) raises -> Bool:
    """Return True when ``total_tokens`` is at/over 75% of ``max_tokens``."""
    var threshold_tokens = Int(Float64(max_tokens) * 0.75)
    return total_tokens >= threshold_tokens
