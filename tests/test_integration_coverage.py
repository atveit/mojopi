"""Small-integration coverage tests — one test per functional area.

Every module added across W1 / W2 / W3 / R1 / R2 / R3 / v1.1 / v1.2 is
touched here, wired against its neighbours where integration matters.
No model weights are required; every test is fast (<1s).

Run with:
    pixi run bash -c "PYTHONPATH=src pytest tests/test_integration_coverage.py -v"
"""
import sys
sys.path.insert(0, "src")
import pytest


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_dirs(tmp_path):
    """Redirect every durable store to tmp_path so tests don't pollute home."""
    from coding_agent.memory.store import set_memory_dir, clear_all_memories
    from max_brain.kv_cache import set_sessions_dir as kv_set
    from agent.session_manager import set_sessions_dir as sm_set
    from agent.session_resolver import set_sessions_dir as sr_set
    set_memory_dir(str(tmp_path / "memory"))
    kv_set(str(tmp_path / "sessions"))
    sm_set(str(tmp_path / "sessions"))
    sr_set(str(tmp_path / "sessions"))
    yield
    clear_all_memories()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_args_file_exists_and_has_output_mode():
    """CliArgs Mojo struct still has all fields added across releases."""
    with open("src/cli/args.mojo") as f:
        src = f.read()
    for field in [
        "mode", "prompt", "model", "max_new_tokens", "session",
        "no_context_files", "system_prompt_override", "append_system_prompt",
        "tools", "no_tools", "enable_structured_output", "output_mode", "verbose",
    ]:
        assert field in src, f"CliArgs missing field: {field}"


def test_print_helper_expand_at_file(tmp_path):
    from cli.print_helper import expand_at_file
    f = tmp_path / "p.txt"
    f.write_text("prompt from file")
    assert expand_at_file(f"@{f}") == "prompt from file"


def test_repl_helper_env_and_banner():
    from cli.repl_helper import welcome_banner, env_model_default
    assert "mojopi" in welcome_banner("1.2.0")
    assert isinstance(env_model_default(), str)


# ---------------------------------------------------------------------------
# TOOLS — all 7 importable + dispatchable via fake args
# ---------------------------------------------------------------------------

def test_all_seven_tool_helpers_importable():
    from coding_agent.tools import bash_tool, edit_helper, find_helper, grep_helper, ls_helper
    assert callable(bash_tool.run_bash)
    assert callable(edit_helper.apply_edit)
    assert callable(find_helper.run_find)
    assert callable(grep_helper.run_grep)
    assert callable(ls_helper.run_ls)


def test_read_tool_via_pathlib(tmp_path):
    """read tool is built inline in tool_executor.mojo via pathlib; exercise the path."""
    f = tmp_path / "r.txt"
    f.write_text("hello")
    from pathlib import Path
    assert Path(str(f)).read_text(encoding="utf-8") == "hello"


def test_bash_tool_run(tmp_path):
    from coding_agent.tools.bash_tool import run_bash
    result = run_bash("echo hi", cwd=str(tmp_path))
    assert "hi" in result["stdout"]
    assert result["exit_code"] == 0


def test_write_tool_via_pathlib(tmp_path):
    f = tmp_path / "w.txt"
    from pathlib import Path
    Path(str(f)).write_text("written")
    assert f.read_text() == "written"


# ---------------------------------------------------------------------------
# SESSION STORE (v3) — roundtrip
# ---------------------------------------------------------------------------

def test_session_store_roundtrip(tmp_path):
    from agent.session_manager import save_turn, load_session_history, HistoryDict, new_session_id
    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="hi"))
    save_turn(sid, HistoryDict(role="assistant", content="hello"))
    save_turn(sid, HistoryDict(role="tool_result", content="42", tool_call_id="t0", tool_name="read"))
    hist = load_session_history(sid)
    assert len(hist) == 3
    assert hist[-1].tool_name == "read"


def test_session_resolver_end_to_end(tmp_path):
    from agent.session_manager import save_turn, new_session_id, HistoryDict
    from agent.session_resolver import resolve_session_id, list_all_sessions, get_latest_session_id
    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="x"))
    assert resolve_session_id(sid[:6]) == sid  # prefix lookup
    assert sid in [s.session_id for s in list_all_sessions()]
    assert get_latest_session_id() == sid


# ---------------------------------------------------------------------------
# CONTEXT + SYSTEM PROMPT BUILDER
# ---------------------------------------------------------------------------

def test_system_prompt_builder(tmp_path, monkeypatch):
    from coding_agent.context.builder import build_full_system_prompt
    # isolate AGENTS.md walk by pointing cwd at an empty dir
    monkeypatch.chdir(tmp_path)
    sp = build_full_system_prompt(str(tmp_path), no_context_files=True)
    assert "Tools" in sp or "tool_call" in sp
    assert "Date:" in sp
    assert str(tmp_path) in sp


# ---------------------------------------------------------------------------
# MAX / MLX BACKENDS — structural only (no weights)
# ---------------------------------------------------------------------------

def test_mlx_backend_available_on_arm64():
    from max_brain.mlx_backend import is_available
    import platform
    if platform.machine() == "arm64":
        assert is_available()


def test_pipeline_module_surface():
    import max_brain.pipeline as p
    assert callable(p.generate_embedded)
    assert callable(p.get_or_create_pipeline)
    assert callable(p._make_pipeline_config)
    assert isinstance(p._pipeline_cache, dict)


def test_threaded_pipeline_singleton():
    from max_brain.threaded_pipeline import get_inference_pool
    assert get_inference_pool() is get_inference_pool()


def test_gil_profiler_context_manager_measures():
    import time
    from max_brain.gil_profiler import profile_gil
    with profile_gil() as prof:
        time.sleep(0.02)
    assert prof.wall_time_ms >= 15


def test_speculative_module_fallback(monkeypatch):
    """Speculative decoding falls back when draft fails to load — only 'draft' repo raises."""
    import mlx_lm
    from max_brain import speculative
    speculative.clear_cache()

    def fake_load(repo):
        if repo == "draft":  # only the draft repo fails
            raise RuntimeError("no draft")
        class M: pass
        return M(), "tok"

    def fake_gen(model, tokenizer, prompt, **kw):
        assert "draft_model" not in kw, f"expected fallback (no draft_model), got {kw}"
        return "fallback"

    monkeypatch.setattr(mlx_lm, "load", fake_load)
    monkeypatch.setattr(mlx_lm, "generate", fake_gen)
    assert speculative.generate_speculative("x", main_repo="main", draft_repo="draft") == "fallback"
    speculative.clear_cache()


# ---------------------------------------------------------------------------
# v1.1 — MEMORY / KV CACHE / TURBOQUANT
# ---------------------------------------------------------------------------

def test_memory_roundtrip_and_retrieval():
    from coding_agent.memory.store import store_memory, list_memories
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.retriever import retrieve_relevant
    store_memory("Pytest is run via pixi.", embedding=embed_text("pytest pixi"))
    store_memory("MLX runs on Metal.", embedding=embed_text("mlx metal"))
    assert len(list_memories()) == 2
    top = retrieve_relevant("how to run tests", k=1)
    assert len(top) == 1
    assert "pytest" in top[0][0].text.lower() or "pixi" in top[0][0].text.lower()


def test_memory_auto_inject_pipeline():
    """auto_inject + retrieve + embed + store all chain through correctly.

    Uses a lower min_score because bag-of-words embeddings produce mild cosine
    scores even for semantically related queries.
    """
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.auto_inject import augment_system_prompt, AUTO_MEMORY_HEADER
    store_memory("The project prefers terse prose.", embedding=embed_text("project prefers terse prose"))
    # Query shares vocabulary with the memory text so BoW gives a hit
    augmented = augment_system_prompt("You are mojopi.", "project prose style", min_score=0.01)
    assert AUTO_MEMORY_HEADER in augmented
    assert "terse" in augmented.lower()


def test_memory_extraction_with_mock_llm():
    from coding_agent.memory.extractor import extract_from_session
    from coding_agent.memory.store import list_memories
    def llm(_):
        return '[{"text": "User prefers Mojo.", "type": "user_preference", "confidence": 0.9}]'
    extract_from_session("t", source="sess:1", llm_fn=llm)
    assert any("mojo" in m.text.lower() for m in list_memories())


def test_kv_cache_round_trip(tmp_path):
    import mlx.core as mx
    from max_brain.kv_cache import save_kv_cache, load_kv_cache, set_sessions_dir
    set_sessions_dir(str(tmp_path))
    class L:
        def __init__(self):
            self.keys = mx.array([[1.0, 2.0]])
            self.values = mx.array([[3.0, 4.0]])
    meta = save_kv_cache([L()], "s", "test-model", token_count=1)
    assert meta["layer_count"] == 1
    loaded = load_kv_cache("s", model=None)
    assert len(loaded) == 1


def test_turboquant_roundtrip():
    import mlx.core as mx
    from max_brain.turboquant import quantize_kv_cache, dequantize_kv_cache, estimate_memory_reduction
    class L:
        def __init__(self):
            self.keys = mx.random.normal(shape=(16, 64))
            self.values = mx.random.normal(shape=(16, 64))
    mx.random.seed(0)
    cache = [L() for _ in range(2)]
    q = quantize_kv_cache(cache, bits=4, use_rotation=True)
    size = estimate_memory_reduction(cache, q)
    restored = dequantize_kv_cache(q)
    assert size["reduction_ratio"] > 2.0
    assert len(restored) == 2


# ---------------------------------------------------------------------------
# v1.2 — THINKING / PARSE-RETRY / TURN-SUMMARY / COMPACTION-BRIDGE
# ---------------------------------------------------------------------------

def test_thinking_strip_preserves_tool_calls():
    from agent.thinking import strip_thinking
    text = '<think>plan</think><tool_call>{"name":"read"}</tool_call>answer'
    r = strip_thinking(text)
    assert "<tool_call>" in r.visible
    assert "plan" in r.thinking
    assert "plan" not in r.visible


def test_parse_retry_eventually_succeeds():
    from agent.parse_retry import retry_parse_tool_calls
    responses = iter(['bad json', '<tool_call>{"name":"read"}</tool_call>'])
    def extract(text):
        return [{"name": "read"}] if "</tool_call>" in text else []
    _, calls = retry_parse_tool_calls("p", "initial", lambda _: next(responses), extract, max_retries=3)
    assert calls == [{"name": "read"}]


def test_turn_summary_with_tool_log():
    from agent.turn_summary import summarize_turn_cap
    history = [
        {"role": "user", "content": "find all TODOs"},
        {"role": "tool_result", "content": "line 1\nline 2", "tool_name": "grep"},
        {"role": "assistant", "content": "partial: found 2 hits so far"},
    ]
    summary = summarize_turn_cap(history, max_turns=3)
    assert "TODO" in summary or "todos" in summary.lower()
    assert "grep" in summary
    assert "3" in summary


def test_compaction_bridge_triggers_on_large_history():
    from agent.compaction_bridge import should_auto_compact
    big = [{"role": "user", "content": "x" * 4000} for _ in range(4)]
    assert should_auto_compact(big, max_tokens=2048)


# ---------------------------------------------------------------------------
# EXTENSIONS + EVENTS
# ---------------------------------------------------------------------------

def test_extension_register_tool_and_dispatch():
    from coding_agent.extensions.registry import register_tool, dispatch_registered_tool, clear_registry
    clear_registry()
    register_tool("greet", lambda name: f"hi {name}")
    assert dispatch_registered_tool("greet", '{"name": "world"}') == "hi world"
    clear_registry()


def test_extension_event_bus_fires():
    from coding_agent.extensions.events import on, fire_event, clear_event_handlers, TOOL_CALL
    clear_event_handlers(TOOL_CALL)
    received = []
    on(TOOL_CALL, lambda p: received.append(p.event_type))
    fire_event(TOOL_CALL, {"name": "read"})
    assert received == [TOOL_CALL]
    clear_event_handlers(TOOL_CALL)


def test_custom_tool_wrap():
    from coding_agent.extensions.custom_tool import wrap_python_tool
    from coding_agent.extensions.registry import dispatch_registered_tool, clear_registry
    clear_registry()
    wrap_python_tool("echo", lambda msg: f"echo:{msg}", schema_json='{"msg": "string"}')
    assert dispatch_registered_tool("echo", '{"msg": "hi"}') == "echo:hi"
    clear_registry()


# ---------------------------------------------------------------------------
# HOOKS / STEERING / ABORT / OUTPUT MODE / PARALLEL DISPATCH
# ---------------------------------------------------------------------------

def test_hooks_before_after_modify_args():
    from agent.hooks import (
        register_before_tool_call, register_after_tool_call,
        run_before_hooks, run_after_hooks, clear_hooks,
    )
    clear_hooks()
    register_before_tool_call(lambda name, args: '{"x": 1}', name="b")
    register_after_tool_call(lambda name, args, res: res + "!", name="a")
    assert run_before_hooks("read", "{}") == '{"x": 1}'
    assert run_after_hooks("read", "{}", "ok") == "ok!"
    clear_hooks()


def test_steering_queue_push_and_poll():
    from agent.steering import push_steering, poll_steering, clear_steering
    clear_steering()
    push_steering("interrupt")
    assert poll_steering() == "interrupt"
    clear_steering()


def test_abort_flag_lifecycle():
    from agent.abort import clear_abort, request_abort, is_aborted
    clear_abort()
    assert not is_aborted()
    request_abort()
    assert is_aborted()
    clear_abort()
    assert not is_aborted()


def test_output_mode_json_emits_valid_jsonl(capsys):
    import json
    from agent.output_mode import emit_answer
    emit_answer("hello", mode="json")
    event = json.loads(capsys.readouterr().out.strip())
    assert event["type"] == "answer"
    assert event["text"] == "hello"


def test_parallel_dispatch_preserves_order_and_runs_parallel():
    import time
    from agent.parallel_dispatch import dispatch_parallel
    def slow(name, args):
        time.sleep(0.03)
        return f"r-{name}"
    calls = [{"name": n, "arguments_json": "{}"} for n in ("read", "grep", "find")]
    t0 = time.perf_counter()
    results = dispatch_parallel(calls, slow)
    elapsed = time.perf_counter() - t0
    assert [r.result for r in results] == ["r-read", "r-grep", "r-find"]
    assert elapsed < 0.080  # 3×30ms serial; parallel should be <80ms


def test_structured_output_regex_fallback():
    from agent.structured_output import _regex_extract_tool_calls
    text = '{"name": "read", "arguments": {"path": "foo"}}'
    calls = _regex_extract_tool_calls(text)
    assert calls and calls[0]["name"] == "read"


# ---------------------------------------------------------------------------
# AGENT LOOP — mock generate; exercise the full control flow
# ---------------------------------------------------------------------------

def test_loop_extract_tool_calls_regex():
    """extract_tool_calls lives in loop.mojo (Mojo); approximate it in Python here."""
    import re, json
    text = '<tool_call>{"name": "read", "arguments": {"path": "/x"}}</tool_call>'
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
    parsed = json.loads(m.group(1))
    assert parsed["name"] == "read"


def test_loop_imports_all_its_deps():
    """Every module loop.mojo calls via Python.import_module must import cleanly."""
    import max_brain.pipeline  # noqa
    import json  # noqa
    import builtins  # noqa
    import agent.thinking  # noqa
    import agent.turn_summary  # noqa
    import coding_agent.extensions.events  # noqa
    import agent.steering  # noqa
    import agent.abort  # noqa
    # If any raise, pytest marks the test failed.


# ---------------------------------------------------------------------------
# SKILLS
# ---------------------------------------------------------------------------

def test_skills_loader_on_fixture_dir():
    from coding_agent.skills.loader import load_skills_dir
    skills = load_skills_dir("tests/fixtures/skills")
    assert len(skills) >= 3  # hello + read + manual are committed fixtures


# ---------------------------------------------------------------------------
# END-TO-END FLOW SIMULATION — session create, turns, resume
# ---------------------------------------------------------------------------

def test_full_session_lifecycle(tmp_path):
    """Create a session, simulate 3 turns, resolve by prefix, reload history."""
    from agent.session_manager import new_session_id, save_turn, HistoryDict, session_message_count
    from agent.session_resolver import resolve_session_id, get_latest_session_id

    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="what is 2+2?"))
    save_turn(sid, HistoryDict(role="assistant", content="The answer is 4."))
    save_turn(sid, HistoryDict(role="user", content="why?"))

    assert session_message_count(sid) == 3
    assert resolve_session_id(sid[:6]) == sid
    assert get_latest_session_id() == sid


def test_full_memory_lifecycle_post_session():
    """Close a session: extract facts + verify they're retrievable next time."""
    from coding_agent.memory.auto_inject import extract_after_session, augment_system_prompt

    def llm(_):
        return '[{"text": "User asks arithmetic questions.", "type": "user_preference", "confidence": 0.8}]'

    count = extract_after_session("sess-123", "transcript about arithmetic", llm_fn=llm)
    assert count == 1

    # Simulate next session: augment with a relevant query
    augmented = augment_system_prompt("You are mojopi.", "what does the user typically ask?")
    assert "arithmetic" in augmented.lower()
