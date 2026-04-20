import sys
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolated_memory_dir(tmp_path, monkeypatch):
    from coding_agent.memory.store import set_memory_dir, clear_all_memories
    set_memory_dir(str(tmp_path))
    yield
    clear_all_memories()


# ---------------------------------------------------------------------------
# Module importability
# ---------------------------------------------------------------------------

def test_store_module_importable():
    from coding_agent.memory import store
    assert hasattr(store, "store_memory")
    assert hasattr(store, "list_memories")


def test_embeddings_module_importable():
    from coding_agent.memory import embeddings
    assert hasattr(embeddings, "embed_text")
    assert hasattr(embeddings, "cosine_similarity")


def test_retriever_module_importable():
    from coding_agent.memory import retriever
    assert hasattr(retriever, "retrieve_relevant")
    assert hasattr(retriever, "format_for_prompt")


def test_extractor_module_importable():
    from coding_agent.memory import extractor
    assert hasattr(extractor, "extract_from_session")


# ---------------------------------------------------------------------------
# MemoryEntry round-trip
# ---------------------------------------------------------------------------

def test_memory_entry_from_dict_round_trip():
    from coding_agent.memory.store import MemoryEntry
    d = {
        "id": "mem_1_abc",
        "text": "Prefers tabs over spaces",
        "embedding": [0.1, 0.2, 0.3],
        "timestamp": "2026-04-19T12:00:00Z",
        "source": "session-1",
        "type": "user_preference",
        "confidence": 0.9,
    }
    entry = MemoryEntry.from_dict(d)
    assert entry.id == "mem_1_abc"
    assert entry.text == "Prefers tabs over spaces"
    assert entry.embedding == [0.1, 0.2, 0.3]
    assert entry.type == "user_preference"
    assert entry.confidence == 0.9
    # Round-trip
    assert entry.to_dict() == d


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def test_bow_embedding_deterministic_and_normalized():
    import math
    from coding_agent.memory.embeddings import _embed_bow
    v1 = _embed_bow("hello world from mojopi")
    v2 = _embed_bow("hello world from mojopi")
    assert v1 == v2
    # Unit-normalized
    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-6
    # Non-empty
    assert any(x != 0.0 for x in v1)


def test_cosine_similarity_of_vector_with_itself_is_one():
    from coding_agent.memory.embeddings import embed_text, cosine_similarity
    v = embed_text("the quick brown fox jumps over the lazy dog", prefer_mlx=False)
    s = cosine_similarity(v, v)
    assert abs(s - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def test_store_memory_appends_to_jsonl_and_cache():
    from coding_agent.memory.store import (
        store_memory, list_memories, MEMORY_FILE,
    )
    from coding_agent.memory.embeddings import embed_text

    vec = embed_text("python 3.12 is required", prefer_mlx=False)
    entry = store_memory(
        text="python 3.12 is required",
        embedding=vec,
        source="session-x",
        type="project_fact",
        confidence=0.95,
    )
    assert entry.id.startswith("mem_")
    assert entry.text == "python 3.12 is required"
    assert entry.type == "project_fact"

    # Cache reflects addition
    all_mems = list_memories()
    assert len(all_mems) == 1
    assert all_mems[0].id == entry.id

    # JSONL file written
    assert MEMORY_FILE.exists()
    contents = MEMORY_FILE.read_text(encoding="utf-8")
    assert entry.id in contents
    assert "python 3.12" in contents


def test_list_memories_filters_by_type():
    from coding_agent.memory.store import store_memory, list_memories
    from coding_agent.memory.embeddings import embed_text

    store_memory("user likes tabs", embed_text("user likes tabs", prefer_mlx=False),
                 type="user_preference")
    store_memory("repo uses pixi", embed_text("repo uses pixi", prefer_mlx=False),
                 type="project_fact")
    store_memory("grep was fast", embed_text("grep was fast", prefer_mlx=False),
                 type="tool_observation")

    all_mems = list_memories()
    assert len(all_mems) == 3

    prefs = list_memories(type="user_preference")
    assert len(prefs) == 1
    assert prefs[0].text == "user likes tabs"

    facts = list_memories(type="project_fact")
    assert len(facts) == 1
    assert facts[0].text == "repo uses pixi"

    tools = list_memories(type="tool_observation")
    assert len(tools) == 1


def test_forget_memory_removes_and_returns_true_false():
    from coding_agent.memory.store import (
        store_memory, list_memories, forget_memory, MEMORY_FILE,
    )
    from coding_agent.memory.embeddings import embed_text

    e1 = store_memory("a", embed_text("a", prefer_mlx=False))
    e2 = store_memory("b", embed_text("b", prefer_mlx=False))

    assert forget_memory(e1.id) is True
    remaining = list_memories()
    assert len(remaining) == 1
    assert remaining[0].id == e2.id

    # JSONL has been rewritten
    contents = MEMORY_FILE.read_text(encoding="utf-8")
    assert e1.id not in contents
    assert e2.id in contents

    # Not found
    assert forget_memory("mem_nonexistent") is False


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

def test_retrieve_relevant_returns_top_k_sorted():
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.retriever import retrieve_relevant

    store_memory("mojo language compiles to native code",
                 embed_text("mojo language compiles to native code", prefer_mlx=False))
    store_memory("python is a dynamic scripting language",
                 embed_text("python is a dynamic scripting language", prefer_mlx=False))
    store_memory("the weather today is sunny",
                 embed_text("the weather today is sunny", prefer_mlx=False))
    store_memory("mlx provides metal-accelerated tensors",
                 embed_text("mlx provides metal-accelerated tensors", prefer_mlx=False))

    results = retrieve_relevant("mojo language compiles", k=2)
    assert len(results) == 2
    # Sorted descending by score
    assert results[0][1] >= results[1][1]
    # Top result should be the most similar one
    assert "mojo" in results[0][0].text.lower()


def test_format_for_prompt_renders_results():
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.retriever import retrieve_relevant, format_for_prompt

    store_memory("user prefers concise replies",
                 embed_text("user prefers concise replies", prefer_mlx=False),
                 type="user_preference", confidence=0.88)

    results = retrieve_relevant("concise replies", k=5)
    assert len(results) >= 1
    text = format_for_prompt(results)
    assert text.startswith("## Relevant memories\n")
    assert "user_preference" in text
    assert "concise" in text
    # Empty case returns empty string
    assert format_for_prompt([]) == ""


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

def test_extract_from_session_parses_valid_json():
    from coding_agent.memory.extractor import extract_from_session
    from coding_agent.memory.store import list_memories

    def mock_llm(prompt: str) -> str:
        return (
            '[{"text": "user prefers dark mode", '
            '"type": "user_preference", "confidence": 0.9}, '
            '{"text": "repo uses pixi for env management", '
            '"type": "project_fact", "confidence": 0.85}]'
        )

    stored = extract_from_session("transcript here", source="sess-1", llm_fn=mock_llm)
    assert len(stored) == 2
    texts = [s["text"] for s in stored]
    assert "user prefers dark mode" in texts
    assert "repo uses pixi for env management" in texts
    # Persisted
    assert len(list_memories()) == 2


def test_extract_from_session_tolerates_prose_around_json():
    from coding_agent.memory.extractor import extract_from_session

    def mock_llm(prompt: str) -> str:
        return (
            "Sure! Here is the extracted JSON:\n\n"
            '[{"text": "user likes tabs", "type": "user_preference", "confidence": 0.7}]'
            "\n\nLet me know if you need more."
        )

    stored = extract_from_session("some transcript", llm_fn=mock_llm)
    assert len(stored) == 1
    assert stored[0]["text"] == "user likes tabs"
    assert stored[0]["type"] == "user_preference"


def test_extract_from_session_returns_empty_on_garbage():
    from coding_agent.memory.extractor import extract_from_session
    from coding_agent.memory.store import list_memories

    def mock_llm(prompt: str) -> str:
        return "I am unable to produce JSON right now. Sorry."

    stored = extract_from_session("transcript", llm_fn=mock_llm)
    assert stored == []
    assert list_memories() == []


# ---------------------------------------------------------------------------
# Admin: clear_all_memories and set_memory_dir
# ---------------------------------------------------------------------------

def test_clear_all_memories_wipes_store_and_file():
    from coding_agent.memory.store import (
        store_memory, list_memories, clear_all_memories, MEMORY_FILE,
    )
    from coding_agent.memory.embeddings import embed_text

    store_memory("a", embed_text("a", prefer_mlx=False))
    store_memory("b", embed_text("b", prefer_mlx=False))
    assert len(list_memories()) == 2
    assert MEMORY_FILE.exists()

    n = clear_all_memories()
    assert n == 2
    assert list_memories() == []
    assert not MEMORY_FILE.exists()


def test_set_memory_dir_redirects_to_tmp(tmp_path):
    from coding_agent.memory import store as store_mod
    from coding_agent.memory.store import (
        set_memory_dir, store_memory, list_memories,
    )
    from coding_agent.memory.embeddings import embed_text

    sub = tmp_path / "redirected"
    set_memory_dir(str(sub))
    store_memory("hello", embed_text("hello", prefer_mlx=False))

    # Module-level MEMORY_FILE should now point inside sub
    assert str(store_mod.MEMORY_FILE).startswith(str(sub))
    assert store_mod.MEMORY_FILE.exists()
    assert len(list_memories()) == 1
