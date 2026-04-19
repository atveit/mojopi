"""Skills loader for mojopi.

Skills are .md files with optional YAML frontmatter. Each skill has:
- name: short identifier (defaults to filename stem)
- description: one-line summary for the system prompt
- trigger: "always" | "when_read_available" | "manual" (default: "always")
- content: the markdown body (everything after the frontmatter)

Skills are loaded from (in order, later overrides earlier by name):
1. Global: ~/.pi/agent/skills/*.md
2. Project: <cwd>/.pi/skills/*.md
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from markdown body.

    Returns (frontmatter_dict, body). If no frontmatter (no leading '---'),
    returns ({}, full_text).
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    fm_text = text[3:end].strip()
    body = text[end + 4:].strip()

    # Minimal YAML parser: key: value lines only (no nested structures).
    # For production, use PyYAML when available and fall back to this.
    fm: dict[str, Any] = {}
    try:
        import yaml
        fm = yaml.safe_load(fm_text) or {}
    except (ImportError, Exception):
        for line in fm_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()

    return fm, body


def load_skill_file(path: str) -> dict[str, Any]:
    """Parse a single skill .md file. Returns a skill dict."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    return {
        "name": fm.get("name", p.stem),
        "description": fm.get("description", ""),
        "trigger": fm.get("trigger", "always"),
        "content": body,
        "source_path": str(p),
    }


def load_skills_dir(directory: str) -> list[dict[str, Any]]:
    """Load all *.md files from directory as skills. Returns list sorted by name."""
    d = Path(directory)
    if not d.is_dir():
        return []
    skills = []
    for p in sorted(d.glob("*.md")):
        try:
            skills.append(load_skill_file(str(p)))
        except Exception:
            pass  # skip unreadable files
    return skills


def load_all_skills(cwd: str = ".", include_global: bool = True) -> list[dict[str, Any]]:
    """Load skills from global (~/.pi/agent/skills/) and project (.pi/skills/) dirs.

    Project skills override global skills with the same name.
    """
    skills_by_name: dict[str, dict] = {}

    if include_global:
        global_dir = Path.home() / ".pi" / "agent" / "skills"
        for s in load_skills_dir(str(global_dir)):
            skills_by_name[s["name"]] = s

    project_dir = Path(cwd) / ".pi" / "skills"
    for s in load_skills_dir(str(project_dir)):
        skills_by_name[s["name"]] = s

    return list(skills_by_name.values())


def filter_skills(skills: list[dict], read_tool_available: bool = True) -> list[dict]:
    """Filter skills by trigger condition.

    - trigger="always" → always included
    - trigger="when_read_available" → only if read_tool_available is True
    - trigger="manual" → never included automatically
    """
    result = []
    for s in skills:
        trigger = s.get("trigger", "always")
        if trigger == "always":
            result.append(s)
        elif trigger == "when_read_available" and read_tool_available:
            result.append(s)
        # trigger="manual" → skip
    return result


def skills_to_system_prompt_section(skills: list[dict]) -> str:
    """Format skills as a section for the system prompt."""
    if not skills:
        return ""
    lines = ["## Skills\n"]
    for s in skills:
        lines.append(f"### {s['name']}")
        if s["description"]:
            lines.append(s["description"])
        lines.append(s["content"])
        lines.append("")
    return "\n".join(lines)
