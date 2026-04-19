from std.python import Python, PythonObject

def load_all_skills(cwd: String, include_global: Bool = True) raises -> PythonObject:
    """Load all skills for this working directory.
    Returns Python list of skill dicts.
    """
    var mod = Python.import_module("coding_agent.skills.loader")
    return mod.load_all_skills(cwd, include_global)

def filter_skills(skills: PythonObject, read_tool_available: Bool = True) raises -> PythonObject:
    """Filter skills by trigger condition. Returns Python list."""
    var mod = Python.import_module("coding_agent.skills.loader")
    return mod.filter_skills(skills, read_tool_available)

def skills_to_system_prompt_section(skills: PythonObject) raises -> String:
    """Format skills as a string for the system prompt."""
    var mod = Python.import_module("coding_agent.skills.loader")
    var result = mod.skills_to_system_prompt_section(skills)
    return String(result)
