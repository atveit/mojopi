from std.python import Python, PythonObject

def dispatch_slash_mojo(line: String, session_id: String, model: String) raises -> String:
    """Return the output string of the slash command (empty if not a slash)."""
    var mod = Python.import_module("cli.slash_commands")
    var state = mod.SlashState(session_id, model)
    var result = mod.dispatch_slash(line, state)
    if not Bool(result.handled):
        return String("")
    return String(result.output)

def help_text_mojo() raises -> String:
    var mod = Python.import_module("cli.slash_commands")
    return String(mod.help_text())
