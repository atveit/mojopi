# System prompt builder — port of pi-mono system-prompt.ts:28-80.
#
# build_system_prompt() assembles the full prompt string from tool descriptions,
# context file contents, date/cwd metadata, and optional project overrides.

from std.collections import List

comptime DEFAULT_PREAMBLE = """You are mojopi, an AI coding assistant running locally via Modular MAX.
You help users understand, write, debug, and refactor code.
You have access to the following tools to inspect and modify the local filesystem."""


def build_system_prompt(
    tool_descriptions: String,
    context_contents: String,
    cwd: String,
    date_str: String,
    system_override: String,
    append_system: String,
) raises -> String:
    """Build the full system prompt string.

    Structure (matches pi-mono system-prompt.ts pattern):
    1. If system_override is non-empty, use it as the base; otherwise use the
       default preamble.
    2. Append tool descriptions section.
    3. Append context files section (if context_contents is non-empty).
    4. Append date + cwd info.
    5. Append append_system (if non-empty).
    """
    var result = String("")

    # 1. Base / preamble.
    if len(system_override) > 0:
        result += system_override.copy()
    else:
        result += DEFAULT_PREAMBLE

    # 2. Tool descriptions section.
    if len(tool_descriptions) > 0:
        result += "\n\n## Tools\n\n"
        result += tool_descriptions.copy()

    # 3. Context files section.
    if len(context_contents) > 0:
        result += "\n\n## Context\n\n"
        result += context_contents.copy()

    # 4. Date + cwd.
    result += "\n\n## Session info\n\n"
    result += "Date: "
    result += date_str.copy()
    result += "\nWorking directory: "
    result += cwd.copy()

    # 5. Append system (project-level addition).
    if len(append_system) > 0:
        result += "\n\n"
        result += append_system.copy()

    return result
