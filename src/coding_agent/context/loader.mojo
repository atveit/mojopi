# Mojo wrapper for the Python context loader.
# Ports pi-mono resource-loader.ts:58-75 via Python interop.
#
# All heavy lifting lives in loader.py; this file provides Mojo-typed entry
# points so the rest of the Mojo codebase can call them without importing
# Python directly at each call site.

from std.python import Python, PythonObject


def find_context_files(cwd: String) raises -> PythonObject:
    """Call Python loader.find_context_files; returns a Python list of paths.

    The returned list is ordered root-first (outermost AGENTS.md/CLAUDE.md
    first), matching the pi-mono resource-loader convention.
    """
    var loader = Python.import_module("coding_agent.context.loader")
    return loader.find_context_files(cwd)


def compose_context(
    cwd: String, no_context_files: Bool = False
) raises -> PythonObject:
    """Call Python loader.compose_context; returns a Python dict.

    Dict keys: 'context_files', 'system_override', 'append_system',
    'global_agents_md'.  See loader.py for full documentation.
    """
    var loader = Python.import_module("coding_agent.context.loader")
    return loader.compose_context(cwd, no_context_files)
