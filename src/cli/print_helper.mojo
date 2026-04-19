from std.python import Python, PythonObject


def expand_at_file(prompt: String) raises -> String:
    var mod = Python.import_module("cli.print_helper")
    var result = mod.expand_at_file(prompt)
    return String(result)


def resolve_prompt(raw: String) raises -> String:
    var mod = Python.import_module("cli.print_helper")
    var result = mod.resolve_prompt(raw)
    return String(result)


def read_stdin_prompt() raises -> String:
    var mod = Python.import_module("cli.print_helper")
    var result = mod.read_stdin_prompt()
    var is_none = Python.evaluate("lambda x: x is None")
    if Bool(is_none(result)):
        return String("")
    return String(result)
