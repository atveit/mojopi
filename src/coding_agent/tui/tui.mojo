from std.python import Python, PythonObject

def run_tui(model: String = String("modularai/Llama-3.1-8B-Instruct-GGUF"), session: String = String("")) raises:
    var tui = Python.import_module("coding_agent.tui.tui")
    _ = tui.run_tui(model, session)

def create_tui_app() raises -> PythonObject:
    var tui = Python.import_module("coding_agent.tui.tui")
    return tui.create_app()
