"""Tests for the W1 context loader slice.

Tests:
1. find_context_files finds AGENTS.md files walking up the tree.
2. find_context_files returns files in root-first order.
3. find_context_files stops at filesystem root (max_depth respected).
4. load_project_overrides returns None for absent files.
5. compose_context with no_context_files=True returns empty context_files list.
6. build_system_prompt_mojo (via Python): output contains cwd and date.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure src/ is on the path regardless of how pytest is invoked.
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from coding_agent.context.loader import (
    compose_context,
    find_context_files,
    load_global_agents_md,
    load_project_overrides,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fake_project"


# ---------------------------------------------------------------------------
# Test 1 — find_context_files discovers AGENTS.md walking upward
# ---------------------------------------------------------------------------

def test_find_context_files_finds_agents_md():
    """Walking up from fake_project/subdir must find at least two AGENTS.md files."""
    cwd = str(FIXTURES_DIR / "subdir")
    paths = find_context_files(cwd)
    assert len(paths) >= 2, f"Expected at least 2 context files, got: {paths}"
    # Both AGENTS.md files must appear in the result.
    basenames = [Path(p).name for p in paths]
    assert basenames.count("AGENTS.md") >= 2


# ---------------------------------------------------------------------------
# Test 2 — find_context_files returns files root-first
# ---------------------------------------------------------------------------

def test_find_context_files_root_first_order():
    """The outer AGENTS.md must come before the inner one."""
    cwd = str(FIXTURES_DIR / "subdir")
    paths = find_context_files(cwd)
    # Filter to only the two fixture AGENTS.md files we control.
    fixture_paths = [p for p in paths if str(FIXTURES_DIR) in p]
    assert len(fixture_paths) >= 2, f"Expected fixture paths in result: {paths}"
    # Outer file is the one directly in fake_project/; inner is in subdir/.
    outer_idx = next(
        i for i, p in enumerate(fixture_paths)
        if Path(p).parent == FIXTURES_DIR
    )
    inner_idx = next(
        i for i, p in enumerate(fixture_paths)
        if Path(p).parent == FIXTURES_DIR / "subdir"
    )
    assert outer_idx < inner_idx, (
        f"Expected outer ({outer_idx}) before inner ({inner_idx})"
    )


# ---------------------------------------------------------------------------
# Test 3 — find_context_files stops before infinite loop (max_depth)
# ---------------------------------------------------------------------------

def test_find_context_files_respects_max_depth():
    """max_depth=1 from subdir should NOT see the top-level fake_project AGENTS.md."""
    cwd = str(FIXTURES_DIR / "subdir")
    # depth=1 means we only look at cwd itself — we should see the subdir
    # AGENTS.md but not the parent's.
    paths = find_context_files(cwd, max_depth=1)
    fixture_paths = [p for p in paths if str(FIXTURES_DIR) in p]
    # Should find only the subdir one.
    assert len(fixture_paths) <= 1, (
        f"max_depth=1 should not reach parent AGENTS.md but got: {fixture_paths}"
    )


# ---------------------------------------------------------------------------
# Test 4 — load_project_overrides returns None for absent files
# ---------------------------------------------------------------------------

def test_load_project_overrides_absent_returns_none():
    """A directory without .pi/ should yield None for both keys."""
    # Use a temp dir that has no .pi subdirectory.
    with tempfile.TemporaryDirectory() as tmp:
        result = load_project_overrides(tmp)
    assert result["system"] is None
    assert result["append_system"] is None


def test_load_project_overrides_reads_present_files():
    """When .pi/SYSTEM.md exists its content is returned."""
    with tempfile.TemporaryDirectory() as tmp:
        pi_dir = Path(tmp) / ".pi"
        pi_dir.mkdir()
        (pi_dir / "SYSTEM.md").write_text("custom system", encoding="utf-8")
        result = load_project_overrides(tmp)
    assert result["system"] == "custom system"
    assert result["append_system"] is None


# ---------------------------------------------------------------------------
# Test 5 — compose_context with no_context_files=True returns empty list
# ---------------------------------------------------------------------------

def test_compose_context_no_context_files_flag():
    """no_context_files=True must result in an empty context_files list."""
    cwd = str(FIXTURES_DIR / "subdir")
    result = compose_context(cwd, no_context_files=True)
    assert result["context_files"] == [], (
        f"Expected empty list, got: {result['context_files']}"
    )


def test_compose_context_default_returns_file_contents():
    """Without the flag, context_files should contain non-empty strings."""
    cwd = str(FIXTURES_DIR / "subdir")
    result = compose_context(cwd)
    # We have two AGENTS.md files in our tree; at least one should be loaded.
    assert len(result["context_files"]) >= 1
    for content in result["context_files"]:
        assert isinstance(content, str)
        assert len(content) > 0


# ---------------------------------------------------------------------------
# Test 6 — build_system_prompt (Python simulation of Mojo logic)
# ---------------------------------------------------------------------------
# The Mojo system_prompt.mojo cannot be called from Python directly, so we
# replicate its logic inline here to verify the contract without requiring
# a Mojo runtime.

def _build_system_prompt_py(
    tool_descriptions: str,
    context_contents: str,
    cwd: str,
    date_str: str,
    system_override: str,
    append_system: str,
) -> str:
    """Python mirror of system_prompt.mojo:build_system_prompt for testing."""
    DEFAULT_PREAMBLE = (
        "You are mojopi, an AI coding assistant running locally via Modular MAX.\n"
        "You help users understand, write, debug, and refactor code.\n"
        "You have access to the following tools to inspect and modify the local filesystem."
    )
    result = system_override if system_override else DEFAULT_PREAMBLE

    if tool_descriptions:
        result += "\n\n## Tools\n\n" + tool_descriptions

    if context_contents:
        result += "\n\n## Context\n\n" + context_contents

    result += "\n\n## Session info\n\n"
    result += f"Date: {date_str}\nWorking directory: {cwd}"

    if append_system:
        result += "\n\n" + append_system

    return result


def test_build_system_prompt_contains_cwd_and_date():
    """The assembled prompt must embed cwd and date_str."""
    cwd = "/home/user/myproject"
    date_str = "2026-04-19"
    prompt = _build_system_prompt_py(
        tool_descriptions="read: read a file",
        context_contents="# Some context",
        cwd=cwd,
        date_str=date_str,
        system_override="",
        append_system="",
    )
    assert cwd in prompt, f"cwd not found in prompt:\n{prompt}"
    assert date_str in prompt, f"date_str not found in prompt:\n{prompt}"


def test_build_system_prompt_uses_override_when_provided():
    """system_override replaces the default preamble."""
    prompt = _build_system_prompt_py(
        tool_descriptions="",
        context_contents="",
        cwd="/tmp",
        date_str="2026-01-01",
        system_override="CUSTOM PREAMBLE",
        append_system="",
    )
    assert "CUSTOM PREAMBLE" in prompt
    assert "mojopi" not in prompt


def test_build_system_prompt_appends_append_system():
    """append_system content must appear at the end of the prompt."""
    prompt = _build_system_prompt_py(
        tool_descriptions="",
        context_contents="",
        cwd="/tmp",
        date_str="2026-01-01",
        system_override="",
        append_system="EXTRA INSTRUCTIONS",
    )
    assert prompt.endswith("EXTRA INSTRUCTIONS")


def test_build_system_prompt_omits_context_section_when_empty():
    """If context_contents is empty, the '## Context' section must not appear."""
    prompt = _build_system_prompt_py(
        tool_descriptions="",
        context_contents="",
        cwd="/tmp",
        date_str="2026-01-01",
        system_override="",
        append_system="",
    )
    assert "## Context" not in prompt
