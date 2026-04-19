from std.python import Python
from agent.types import ParsedToolCall
from agent.hooks import run_before_hooks, run_after_hooks

def dispatch_tool(name: String, arguments_json: String) raises -> String:
    """Dispatch a tool call by name. Returns the tool result as a string.

    Runs before/after hooks around the actual dispatch (best-effort).
    """
    # Run before hooks — may modify arguments_json
    var actual_args = arguments_json
    try:
        actual_args = run_before_hooks(name, arguments_json)
    except:
        pass  # hooks are best-effort

    var result = _dispatch_tool_impl(name, actual_args)

    # Run after hooks — may modify result
    try:
        result = run_after_hooks(name, actual_args, result)
    except:
        pass  # hooks are best-effort

    return result

def _dispatch_tool_impl(name: String, arguments_json: String) raises -> String:
    """Internal tool dispatch implementation. W2 scope: dispatches to Python helpers for the 7 tools.
    Unknown tool names return an error string.
    """
    var py_json = Python.import_module("json")
    var builtins = Python.import_module("builtins")
    var args = py_json.loads(arguments_json)

    if name == "read":
        var path_py = args.get("path", "")
        # For W2, use Python pathlib directly
        var py_path = Python.import_module("pathlib")
        var content = py_path.Path(String(path_py)).read_text(encoding="utf-8")
        return String(content)

    elif name == "bash":
        var cmd_py = args.get("command", "")
        var mod = Python.import_module("coding_agent.tools.bash_tool")
        var result = mod.run_bash(String(cmd_py))
        return String(result["stdout"]) + String(result["stderr"])

    elif name == "write":
        var path_py = args.get("path", "")
        var content_py = args.get("content", "")
        var py_path = Python.import_module("pathlib")
        _ = py_path.Path(String(path_py)).write_text(String(content_py), encoding="utf-8")
        return String("wrote ") + String(path_py)

    elif name == "edit":
        var mod = Python.import_module("coding_agent.tools.edit_helper")
        var result = mod.apply_edit(
            String(args.get("path", "")),
            String(args.get("old_string", "")),
            String(args.get("new_string", "")),
        )
        if Bool(result["success"]):
            return String("edit applied successfully")
        else:
            return String("edit failed: ") + String(result["error"])

    elif name == "grep":
        var mod = Python.import_module("coding_agent.tools.grep_helper")
        var result = mod.run_grep(
            String(args.get("pattern", "")),
            String(args.get("path", ".")),
        )
        var matches = result["matches"]
        var out = String("")
        var n = Int(py=builtins.len(matches))
        for i in range(n):
            var m = matches[i]
            out += String(m["file"]) + String(":") + String(m["line"]) + String(": ") + String(m["text"]) + String("\n")
        return out

    elif name == "find":
        var mod = Python.import_module("coding_agent.tools.find_helper")
        var result = mod.run_find(String(args.get("directory", ".")))
        var paths = result["paths"]
        var out = String("")
        var n = Int(py=builtins.len(paths))
        for i in range(n):
            out += String(paths[i]) + String("\n")
        return out

    elif name == "ls":
        var mod = Python.import_module("coding_agent.tools.ls_helper")
        var result = mod.run_ls(String(args.get("path", ".")))
        var entries = result["entries"]
        var out = String("")
        var n = Int(py=builtins.len(entries))
        for i in range(n):
            var e = entries[i]
            out += String(e["name"]) + String("\n")
        return out

    else:
        return String("error: unknown tool: ") + name
