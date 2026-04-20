from std.python import Python, PythonObject
from std.collections import List

def store_memory_text(text: String, source: String = String(""), type: String = String("project_fact"), confidence: Float64 = 1.0) raises -> String:
    """Store a new memory entry. Returns the entry id."""
    var emb_mod = Python.import_module("coding_agent.memory.embeddings")
    var store_mod = Python.import_module("coding_agent.memory.store")
    var vec = emb_mod.embed_text(text)
    var entry = store_mod.store_memory(text, vec, source, type, confidence)
    return String(entry.id)

def retrieve_relevant_text(query: String, k: Int = 5) raises -> String:
    """Return relevant memories formatted for prompt injection."""
    var retr = Python.import_module("coding_agent.memory.retriever")
    var results = retr.retrieve_relevant(query, k)
    return String(retr.format_for_prompt(results))

def memory_count() raises -> Int:
    var store_mod = Python.import_module("coding_agent.memory.store")
    var builtins = Python.import_module("builtins")
    return Int(py=builtins.len(store_mod.list_memories()))
