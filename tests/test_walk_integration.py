"""Walk-tier integration tests — realistic multi-turn agent scenarios.

These tests exercise full workflows a real pi-mono user would hit:
  - "Explain this file" → multi-turn read+summarize chain
  - "Find all TODOs and show them" → grep+read chain
  - "Edit config and re-run tests" → read+edit+bash chain
  - Session resume across process invocations
  - Memory retrieval actually influencing a turn
  - Compaction triggering on long sessions
  - Extension-registered tools being invoked
  - Abort mid-turn, steering mid-turn

The model is mocked so tests are deterministic and fast (<2 s).
A parallel run-tier suite (test_run_integration.py) uses the same scenarios
against a real Llama model.
"""
import sys
sys.path.insert(0, "src")
import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# FIXTURES — isolate every durable store
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate(tmp_path):
    from coding_agent.memory.store import set_memory_dir, clear_all_memories
    from agent.session_manager import set_sessions_dir as sm_set
    from agent.session_resolver import set_sessions_dir as sr_set
    set_memory_dir(str(tmp_path / "memory"))
    sm_set(str(tmp_path / "sessions"))
    sr_set(str(tmp_path / "sessions"))
    yield
    clear_all_memories()


# ---------------------------------------------------------------------------
# PYTHON-SIDE AGENT LOOP REPLICA
#
# The real loop lives in loop.mojo (compiled); for fast walk-tier tests we
# run a Python equivalent that calls all the same helper modules. This lets
# us mock the LLM and script exact response sequences deterministically.
# ---------------------------------------------------------------------------

def _python_run_loop(
    user_input: str,
    system_prompt: str,
    dispatch_tool_fn,
    generate_fn,
    max_turns: int = 10,
):
    """A Python mirror of loop.mojo's run_loop for integration testing.

    Calls the same real helper modules: thinking.strip_thinking_text,
    turn_summary.summarize_turn_cap, extensions.events.fire_event.
    """
    from agent.thinking import strip_thinking_text
    from agent.turn_summary import summarize_turn_cap
    from coding_agent.extensions.events import fire_event
    from agent.abort import clear_abort, is_aborted
    from agent.steering import poll_steering, clear_steering
    import re

    clear_abort()
    clear_steering()
    fire_event("before_agent_start", {})

    history = [{"role": "user", "content": user_input, "tool_call_id": "", "tool_name": ""}]

    for turn in range(max_turns):
        if is_aborted():
            return "[aborted]", history

        steering = poll_steering()
        if steering:
            history.append({"role": "user", "content": f"[user] {steering}", "tool_call_id": "", "tool_name": ""})

        prompt_text = system_prompt + "\n\n" + _format_history(history)
        fire_event("message_start", {})
        response = generate_fn(prompt_text)
        fire_event("message_end", {})

        response = strip_thinking_text(response)

        # Extract <tool_call>{...}</tool_call> blocks
        calls = []
        for m in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL):
            try:
                calls.append(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass

        if not calls:
            return response, history

        history.append({"role": "assistant", "content": response, "tool_call_id": "", "tool_name": ""})

        for i, call in enumerate(calls):
            if is_aborted():
                return "[aborted during tool execution]", history
            name = call.get("name", "")
            args = json.dumps(call.get("arguments", {}))
            result = dispatch_tool_fn(name, args)
            history.append({
                "role": "tool_result",
                "content": result,
                "tool_call_id": f"tc_{turn}_{i}",
                "tool_name": name,
            })

    # Max turns hit — use real turn_summary
    return summarize_turn_cap(history, max_turns=max_turns), history


def _format_history(history: list[dict]) -> str:
    """Tiny ChatML-ish serializer for the mock prompt."""
    lines = []
    for h in history:
        lines.append(f"{h['role']}: {h['content']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SCENARIO 1 — explain this file: ls → read → summarize
# ---------------------------------------------------------------------------

def test_walk_explain_file_scenario(tmp_path):
    """User: 'Tell me what README.md contains.'

    Agent should call read, get the content, then summarize."""
    readme = tmp_path / "README.md"
    readme.write_text("# Widget\nWidget is a local AI assistant.")

    scripted_responses = iter([
        # Turn 1: call read
        f'<tool_call>{{"name": "read", "arguments": {{"path": "{readme}"}}}}</tool_call>',
        # Turn 2: summarize (no more tool calls → final answer)
        "The file describes Widget, a local AI assistant.",
    ])

    def fake_dispatch(name, args_json):
        args = json.loads(args_json)
        if name == "read":
            return Path(args["path"]).read_text()
        return f"error: unknown tool {name}"

    def fake_generate(prompt):
        return next(scripted_responses)

    final, history = _python_run_loop(
        f"Tell me what {readme} contains.",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )
    assert "Widget" in final
    assert "local AI assistant" in final
    # Verify the tool-result turn was added
    tool_results = [h for h in history if h["role"] == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0]["tool_name"] == "read"


# ---------------------------------------------------------------------------
# SCENARIO 2 — find TODOs: grep → read → summarize
# ---------------------------------------------------------------------------

def test_walk_find_todos_scenario(tmp_path):
    """User: 'Find all TODOs in the repo.'"""
    (tmp_path / "a.py").write_text("x = 1  # TODO: fix\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    (tmp_path / "c.py").write_text("# TODO: cleanup\n# TODO: docs\n")

    scripted_responses = iter([
        f'<tool_call>{{"name": "grep", "arguments": {{"pattern": "TODO", "path": "{tmp_path}"}}}}</tool_call>',
        "Found 3 TODOs across a.py and c.py.",
    ])

    def fake_dispatch(name, args_json):
        args = json.loads(args_json)
        if name == "grep":
            from coding_agent.tools.grep_helper import run_grep
            result = run_grep(args["pattern"], args["path"])
            return "\n".join(f"{m['file']}:{m['line']}: {m['text']}" for m in result["matches"])
        return "?"

    def fake_generate(prompt):
        return next(scripted_responses)

    final, history = _python_run_loop(
        "Find all TODOs",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )
    assert "3" in final or "TODO" in final
    tool_results = [h for h in history if h["role"] == "tool_result"]
    assert tool_results[0]["tool_name"] == "grep"


# ---------------------------------------------------------------------------
# SCENARIO 3 — edit + run tests: read → edit → bash → report
# ---------------------------------------------------------------------------

def test_walk_edit_and_verify_scenario(tmp_path):
    """User: 'Change x=1 to x=42 in config.py and verify it still parses.'"""
    config = tmp_path / "config.py"
    config.write_text("x = 1\ny = 2\n")

    scripted_responses = iter([
        f'<tool_call>{{"name": "read", "arguments": {{"path": "{config}"}}}}</tool_call>',
        f'<tool_call>{{"name": "edit", "arguments": {{"path": "{config}", "old_string": "x = 1", "new_string": "x = 42"}}}}</tool_call>',
        f'<tool_call>{{"name": "bash", "arguments": {{"command": "python -c \\"import ast; ast.parse(open(\'{config}\').read()); print(\'OK\')\\""}}}}</tool_call>',
        "Changed x=1 to x=42 in config.py. Parse check passed.",
    ])

    def fake_dispatch(name, args_json):
        args = json.loads(args_json)
        if name == "read":
            return Path(args["path"]).read_text()
        if name == "edit":
            from coding_agent.tools.edit_helper import apply_edit
            r = apply_edit(args["path"], args["old_string"], args["new_string"])
            return "edit applied" if r["success"] else f"edit failed: {r['error']}"
        if name == "bash":
            from coding_agent.tools.bash_tool import run_bash
            r = run_bash(args["command"])
            return r["stdout"] + r["stderr"]
        return "?"

    def fake_generate(prompt):
        return next(scripted_responses)

    final, history = _python_run_loop(
        f"Change x=1 to x=42 in {config}",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )

    # The edit actually happened on disk
    assert config.read_text() == "x = 42\ny = 2\n"
    # All three tool types were called
    tool_names = [h["tool_name"] for h in history if h["role"] == "tool_result"]
    assert tool_names == ["read", "edit", "bash"]
    # bash output should show OK
    bash_result = [h for h in history if h.get("tool_name") == "bash"][0]
    assert "OK" in bash_result["content"]


# ---------------------------------------------------------------------------
# SCENARIO 4 — session resume across process invocations
# ---------------------------------------------------------------------------

def test_walk_session_resume_across_runs(tmp_path):
    """Two 'process invocations' — second resumes the first's session."""
    from agent.session_manager import (
        new_session_id, save_turn, load_session_history, HistoryDict,
    )
    from agent.session_resolver import resolve_session_id

    # Run 1: create session, save 3 turns
    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="what is 2+2?"))
    save_turn(sid, HistoryDict(role="assistant", content="4"))
    save_turn(sid, HistoryDict(role="user", content="why?"))

    # Run 2: user supplies a prefix, we rehydrate
    prefix = sid[:6]
    resumed = resolve_session_id(prefix)
    history = load_session_history(resumed)

    assert resumed == sid
    assert len(history) == 3
    assert history[0].content == "what is 2+2?"
    assert history[-1].content == "why?"


# ---------------------------------------------------------------------------
# SCENARIO 5 — memory retrieval changes the system prompt
# ---------------------------------------------------------------------------

def test_walk_memory_retrieval_influences_prompt():
    """Store a fact, make a related query, verify fact appears in augmented prompt."""
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.auto_inject import augment_system_prompt

    store_memory(
        "The user strongly prefers pathlib over os.path in Python code.",
        embedding=embed_text("pathlib python path"),
    )
    augmented = augment_system_prompt(
        base_prompt="You are a coding assistant.",
        query="pathlib python path handling",
        min_score=0.01,
    )
    assert "pathlib" in augmented.lower()
    # And the base prompt is preserved
    assert augmented.startswith("You are a coding assistant.")


# ---------------------------------------------------------------------------
# SCENARIO 6 — compaction triggers on long sessions
# ---------------------------------------------------------------------------

def test_walk_compaction_triggers_over_budget():
    """Build a long history, verify compaction triggers + shortens."""
    from agent.compaction_bridge import should_auto_compact, auto_compact_if_needed
    # 40 turns × 2000 chars = 80000 chars ≈ 20000 tokens, well over 2048 × 0.5
    history = [
        {"role": "user", "content": "x" * 2000, "tool_call_id": "", "tool_name": ""}
        for _ in range(40)
    ]
    assert should_auto_compact(history, max_tokens=2048, threshold=0.5)
    compacted, was = auto_compact_if_needed(history, max_tokens=2048, threshold=0.5)
    assert was is True
    # Compacted must not be empty (summary + last-N preserved)
    assert len(compacted) > 0


# ---------------------------------------------------------------------------
# SCENARIO 7 — extension-registered tool fires in loop
# ---------------------------------------------------------------------------

def test_walk_extension_tool_invoked_in_loop():
    """User extension registers a tool; loop dispatches it; result flows back."""
    from coding_agent.extensions.registry import (
        register_tool, dispatch_registered_tool, clear_registry,
    )
    clear_registry()
    register_tool(
        "ticket_lookup",
        lambda id: f"Ticket {id}: Fix TurboQuant rotation",
        description="Look up a Linear ticket",
        schema_json='{"id": "string"}',
    )

    scripted_responses = iter([
        '<tool_call>{"name": "ticket_lookup", "arguments": {"id": "ABC-123"}}</tool_call>',
        "The ticket is about fixing TurboQuant rotation.",
    ])

    def fake_dispatch(name, args_json):
        # Route extension tools through the registry
        try:
            return dispatch_registered_tool(name, args_json)
        except KeyError:
            return f"unknown tool: {name}"

    def fake_generate(prompt):
        return next(scripted_responses)

    final, history = _python_run_loop(
        "Look up ticket ABC-123",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )

    assert "TurboQuant" in final
    tool_results = [h for h in history if h["role"] == "tool_result"]
    assert tool_results[0]["tool_name"] == "ticket_lookup"
    assert "TurboQuant" in tool_results[0]["content"]

    clear_registry()


# ---------------------------------------------------------------------------
# SCENARIO 8 — abort mid-turn cuts the loop
# ---------------------------------------------------------------------------

def test_walk_abort_mid_turn():
    """Abort set from INSIDE generate fn is observed before the next turn."""
    from agent.abort import request_abort, is_aborted, clear_abort

    call_count = [0]

    def fake_dispatch(*a, **k):
        return "ok"

    def fake_generate(prompt):
        call_count[0] += 1
        # First call: emit a tool call so the loop continues
        if call_count[0] == 1:
            # After responding, set abort so the NEXT iteration bails
            request_abort()
            return '<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>'
        # Should never be reached — abort fires before this
        pytest.fail("generate called after abort was set")

    final, history = _python_run_loop(
        "long task",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )
    assert "abort" in final.lower()
    clear_abort()


# ---------------------------------------------------------------------------
# SCENARIO 9 — steering message injected into loop
# ---------------------------------------------------------------------------

def test_walk_steering_injects_user_turn():
    """Steering pushed from INSIDE turn 1 gets polled at the top of turn 2."""
    from agent.steering import push_steering, clear_steering

    call_count = [0]

    def fake_dispatch(name, args_json):
        return "results"

    def fake_generate(prompt):
        call_count[0] += 1
        if call_count[0] == 1:
            # Push steering so the NEXT turn polls and injects it
            push_steering("actually use grep instead")
            return '<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>'
        # Turn 2: the steering has already been injected into history before generate
        return "acknowledged — using grep now"

    final, history = _python_run_loop(
        "find foo",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )

    # The injected steering should appear as an extra user turn
    steering_turns = [
        h for h in history
        if h["role"] == "user" and "actually use grep" in h["content"]
    ]
    assert len(steering_turns) == 1
    clear_steering()


# ---------------------------------------------------------------------------
# SCENARIO 10 — turn-cap produces summary instead of placeholder
# ---------------------------------------------------------------------------

def test_walk_turn_cap_produces_summary():
    """Never-ending tool calls → turn-cap → summary includes history."""
    def fake_dispatch(name, args_json):
        return "ok"

    # Always emit a tool call, never conclude — force the cap.
    def fake_generate(prompt):
        return '<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>'

    final, history = _python_run_loop(
        "do the thing",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
        max_turns=3,  # low cap to hit quickly
    )
    # summarize_turn_cap output mentions the user's request
    assert "do the thing" in final or "3" in final
    # Should have hit multiple tool calls
    tool_results = [h for h in history if h["role"] == "tool_result"]
    assert len(tool_results) >= 3


# ---------------------------------------------------------------------------
# SCENARIO 11 — thinking tokens don't confuse tool extraction
# ---------------------------------------------------------------------------

def test_walk_reasoning_model_tool_call():
    """Reasoning model response: <think>plan</think><tool_call>...</tool_call>."""
    scripted = iter([
        '<think>I need to read the file first.</think>'
        '<tool_call>{"name": "read", "arguments": {"path": "/tmp/x"}}</tool_call>',
        "Done.",
    ])

    def fake_dispatch(name, args_json):
        return "contents"

    def fake_generate(prompt):
        return next(scripted)

    final, history = _python_run_loop(
        "read /tmp/x",
        "You are an agent.",
        fake_dispatch,
        fake_generate,
    )
    # The tool was called (thinking didn't swallow the tool_call tag)
    tool_results = [h for h in history if h["role"] == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0]["tool_name"] == "read"


# ---------------------------------------------------------------------------
# SCENARIO 12 — session + memory + tool chain end-to-end
# ---------------------------------------------------------------------------

def test_walk_session_memory_tool_chain_together():
    """Run a session that persists turns, stores a fact, and calls a tool."""
    from agent.session_manager import new_session_id, save_turn, HistoryDict, load_session_history
    from coding_agent.memory.store import store_memory
    from coding_agent.memory.embeddings import embed_text
    from coding_agent.memory.auto_inject import augment_system_prompt

    # Prior session memory
    store_memory(
        "The project root is /Users/amund/mojopi/mojopi.",
        embedding=embed_text("project root mojopi"),
    )

    sid = new_session_id()
    save_turn(sid, HistoryDict(role="user", content="what is the project root?"))

    augmented = augment_system_prompt(
        "You are a coding agent.",
        query="project root path",
        min_score=0.01,
    )
    assert "mojopi" in augmented.lower()

    # Save an assistant turn that uses the injected fact
    save_turn(sid, HistoryDict(role="assistant", content="The project root is /Users/amund/mojopi/mojopi."))

    history = load_session_history(sid)
    assert len(history) == 2
    assert "mojopi" in history[-1].content
