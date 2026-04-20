"""Tests for coding_agent/memory/auto_inject.py — automatic memory injection."""
import sys
sys.path.insert(0, "src")
import pytest


@pytest.fixture(autouse=True)
def _isolated_memory(tmp_path):
    from coding_agent.memory.store import set_memory_dir, clear_all_memories
    set_memory_dir(str(tmp_path))
    yield
    clear_all_memories()


def test_module_importable():
    from coding_agent.memory import auto_inject
    assert hasattr(auto_inject, "augment_system_prompt")
    assert hasattr(auto_inject, "extract_after_session")
    assert hasattr(auto_inject, "should_inject_memory")


def test_augment_with_empty_store_returns_base():
    from coding_agent.memory.auto_inject import augment_system_prompt
    base = "You are mojopi."
    assert augment_system_prompt(base, "hello") == base


def test_augment_with_empty_query_returns_base():
    from coding_agent.memory.auto_inject import augment_system_prompt
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    store_memory("fact", embedding=embed_text("fact"))
    base = "You are mojopi."
    assert augment_system_prompt(base, "") == base
    assert augment_system_prompt(base, "   ") == base


def test_augment_appends_memories_section():
    from coding_agent.memory.auto_inject import augment_system_prompt, AUTO_MEMORY_HEADER
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    store_memory("Tests run via pixi.", embedding=embed_text("pixi tests"))
    result = augment_system_prompt("You are mojopi.", "how to run tests")
    assert AUTO_MEMORY_HEADER in result
    assert "pixi" in result.lower() or "tests" in result.lower()


def test_augment_preserves_base_text():
    from coding_agent.memory.auto_inject import augment_system_prompt
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    store_memory("x", embedding=embed_text("x"))
    base = "You are mojopi. Your task is to help."
    result = augment_system_prompt(base, "x")
    assert result.startswith(base)


def test_augment_filters_low_score_noise():
    """With very low relevance, augment should still return base when no hit above min_score."""
    from coding_agent.memory.auto_inject import augment_system_prompt
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    store_memory("totally unrelated content", embedding=embed_text("totally unrelated content"))
    base = "You are mojopi."
    # Query no meaningful overlap with BoW bag
    result = augment_system_prompt(base, "zyzzyx", k=3, min_score=0.9)
    assert result == base


def test_extract_after_session_with_mock_llm():
    from coding_agent.memory.auto_inject import extract_after_session
    from coding_agent.memory.store import list_memories

    def mock_llm(prompt: str) -> str:
        return '[{"text": "User prefers brevity.", "type": "user_preference", "confidence": 0.9}]'

    count = extract_after_session("sess-1", "transcript body", llm_fn=mock_llm)
    assert count == 1
    mems = list_memories()
    assert any("brevity" in m.text for m in mems)


def test_extract_after_session_empty_transcript():
    from coding_agent.memory.auto_inject import extract_after_session
    assert extract_after_session("sess-1", "") == 0
    assert extract_after_session("sess-1", "   \n\n  ") == 0


def test_extract_after_session_never_raises():
    """extractor failure must be swallowed so session close is never blocked."""
    from coding_agent.memory.auto_inject import extract_after_session

    def bad_llm(prompt: str) -> str:
        raise RuntimeError("llm exploded")

    # Should return 0, NOT propagate RuntimeError
    assert extract_after_session("sess-1", "transcript", llm_fn=bad_llm) == 0


def test_should_inject_memory_defaults_true(monkeypatch):
    from coding_agent.memory.auto_inject import should_inject_memory
    monkeypatch.delenv("MOJOPI_AUTO_MEMORY", raising=False)
    assert should_inject_memory() is True


def test_should_inject_memory_respects_env(monkeypatch):
    from coding_agent.memory.auto_inject import should_inject_memory
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv("MOJOPI_AUTO_MEMORY", v)
        assert should_inject_memory() is False
    for v in ("1", "true", "yes", "anything"):
        monkeypatch.setenv("MOJOPI_AUTO_MEMORY", v)
        assert should_inject_memory() is True
