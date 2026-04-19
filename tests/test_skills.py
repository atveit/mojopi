import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures', 'skills')

def test_parse_frontmatter_present():
    from coding_agent.skills.loader import _parse_frontmatter
    text = "---\nname: foo\ndescription: bar\n---\n\nBody text"
    fm, body = _parse_frontmatter(text)
    assert fm["name"] == "foo"
    assert "Body text" in body

def test_parse_frontmatter_absent():
    from coding_agent.skills.loader import _parse_frontmatter
    text = "No frontmatter here"
    fm, body = _parse_frontmatter(text)
    assert fm == {}
    assert body == text

def test_load_skill_file_hello():
    from coding_agent.skills.loader import load_skill_file
    path = os.path.join(FIXTURES, "hello_skill.md")
    s = load_skill_file(path)
    assert s["name"] == "hello_skill"
    assert s["trigger"] == "always"
    assert "Hello there!" in s["content"]

def test_load_skill_file_no_frontmatter():
    from coding_agent.skills.loader import load_skill_file
    path = os.path.join(FIXTURES, "no_frontmatter.md")
    s = load_skill_file(path)
    assert s["name"] == "no_frontmatter"  # defaults to stem
    assert s["trigger"] == "always"

def test_load_skills_dir():
    from coding_agent.skills.loader import load_skills_dir
    skills = load_skills_dir(FIXTURES)
    assert len(skills) == 4
    names = [s["name"] for s in skills]
    assert "hello_skill" in names
    assert "read_skill" in names

def test_load_skills_dir_nonexistent():
    from coding_agent.skills.loader import load_skills_dir
    skills = load_skills_dir("/nonexistent/path/xyz")
    assert skills == []

def test_filter_skills_always():
    from coding_agent.skills.loader import filter_skills
    skills = [
        {"name": "a", "trigger": "always"},
        {"name": "b", "trigger": "manual"},
        {"name": "c", "trigger": "when_read_available"},
    ]
    result = filter_skills(skills, read_tool_available=False)
    assert len(result) == 1
    assert result[0]["name"] == "a"

def test_filter_skills_read_available():
    from coding_agent.skills.loader import filter_skills
    skills = [
        {"name": "a", "trigger": "always"},
        {"name": "b", "trigger": "manual"},
        {"name": "c", "trigger": "when_read_available"},
    ]
    result = filter_skills(skills, read_tool_available=True)
    assert len(result) == 2
    names = [s["name"] for s in result]
    assert "a" in names
    assert "c" in names

def test_skills_to_system_prompt_section_empty():
    from coding_agent.skills.loader import skills_to_system_prompt_section
    assert skills_to_system_prompt_section([]) == ""

def test_skills_to_system_prompt_section_content():
    from coding_agent.skills.loader import skills_to_system_prompt_section
    skills = [{"name": "mys kill", "description": "desc", "content": "Do X.", "trigger": "always"}]
    section = skills_to_system_prompt_section(skills)
    assert "## Skills" in section
    assert "Do X." in section

def test_load_all_skills_uses_project_dir(tmp_path):
    from coding_agent.skills.loader import load_all_skills
    pi_dir = tmp_path / ".pi" / "skills"
    pi_dir.mkdir(parents=True)
    (pi_dir / "test.md").write_text("---\nname: test_skill\n---\nTest content.", encoding="utf-8")
    skills = load_all_skills(str(tmp_path), include_global=False)
    assert len(skills) == 1
    assert skills[0]["name"] == "test_skill"
