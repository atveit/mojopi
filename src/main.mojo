from std.sys import argv
from std.python import Python
from std.collections import List

from cli.args import parse_args, argv_to_list, CliArgs, ParseResult
from cli.print_helper import resolve_prompt, read_stdin_prompt
from max_brain.inference import get_max_version
from agent.types import AgentContext, HistoryEntry, AgentTool
from agent.loop import run_loop
from agent.output_mode import emit_answer, emit_error, is_valid_mode

comptime VERSION = "1.2.0"


def print_usage():
    print("usage: mojopi [options]")
    print("")
    print("  -p, --print <prompt>           one-shot print mode (no REPL)")
    print("  --version                      print version and exit")
    print("  --model <hf-repo>              model repo (default: modularai/Llama-3.1-8B-Instruct-GGUF)")
    print("  --max-new-tokens N             token cap (default: 512)")
    print("  --session <id>                 resume session (uuid prefix or path)")
    print("  --no-context-files             skip AGENTS.md / CLAUDE.md loading")
    print("  --tools t1,t2                  restrict to named tools")
    print("  --no-tools                     disable all tools")
    print("  --system-prompt <text>         override system prompt")
    print("  --append-system-prompt <text>  append to system prompt")
    print("  --enable-structured-output     use JSON-schema grammar (GPU only)")
    print("  --mode json|rpc|print          output mode (default: print)")
    print("  --verbose / -v                 verbose output")
    print("")
    print("  Prompt can be @filepath to read from file.")
    print("  With no -p, mojopi runs an interactive REPL.")


def _build_context(args: CliArgs) raises -> AgentContext:
    """Build the AgentContext (system prompt + tools) from parsed CLI args."""
    var builder = Python.import_module("coding_agent.context.builder")
    var os_mod = Python.import_module("os")
    var cwd = String(os_mod.getcwd())
    var sys_prompt = String(builder.build_full_system_prompt(
        cwd,
        args.no_context_files,
        args.system_prompt_override,
        args.append_system_prompt,
    ))

    var tools = List[AgentTool]()
    if not args.no_tools:
        tools.append(AgentTool(String("read"), String("Read a file"), String("{}")))
        tools.append(AgentTool(String("write"), String("Write a file"), String("{}")))
        tools.append(AgentTool(String("edit"), String("Edit a file"), String("{}")))
        tools.append(AgentTool(String("bash"), String("Run a shell command"), String("{}")))
        tools.append(AgentTool(String("grep"), String("Search for a pattern"), String("{}")))
        tools.append(AgentTool(String("find"), String("List files under a directory"), String("{}")))
        tools.append(AgentTool(String("ls"), String("List a directory"), String("{}")))

    return AgentContext(sys_prompt, tools^, args.model.copy())


def _resolve_or_new_session(session_arg: String) raises -> String:
    """If session_arg is empty → new session id; otherwise resolve prefix → full id."""
    var sm = Python.import_module("agent.session_manager")
    var sr = Python.import_module("agent.session_resolver")
    if len(session_arg) == 0:
        return String(sm.new_session_id())
    try:
        return String(sr.resolve_session_id(session_arg))
    except:
        print("mojopi: warning: could not resolve --session", session_arg, "— starting new session")
        return String(sm.new_session_id())


def _run_interactive(args: CliArgs) raises:
    var builtins = Python.import_module("builtins")
    var repl = Python.import_module("cli.repl_helper")
    var sm = Python.import_module("agent.session_manager")
    print(String(repl.welcome_banner(VERSION)))

    var ctx = _build_context(args)
    var session_id = _resolve_or_new_session(args.session)

    # Rehydrate existing history count, if any, so users know they're resuming.
    var n_prior = Int(py=sm.session_message_count(session_id))
    var py_sid = Python.import_module("builtins").str(session_id)
    var short_id = String(py_sid[:8])
    if n_prior > 0:
        print("(resumed session ", short_id, " with ", n_prior, " prior messages)")
    else:
        print("(new session ", short_id, ")")

    while True:
        print("")
        var line = String(builtins.input("> "))
        var stripped = line.strip()
        if len(stripped) == 0:
            continue
        if stripped == "/exit" or stripped == "/quit":
            return
        if stripped == "/help":
            print("  /exit, /quit           exit")
            print("  /clear                 clear screen")
            print("  /version               print version")
            print("  /file <path>           load file contents into next message")
            print("  /session               print current session id")
            print("  anything else          send to agent")
            continue
        if stripped == "/clear":
            print("\033[2J\033[H")
            continue
        if stripped == "/version":
            var v = get_max_version()
            print("mojopi", VERSION, "/ max:", v)
            continue
        if stripped == "/session":
            print("session:", session_id)
            continue
        if stripped.startswith("/file "):
            var py_stripped = Python.import_module("builtins").str(stripped)
            var path = String(py_stripped[6:].strip())
            try:
                var contents = String(repl.read_file_for_slash_command(path))
                line = String("Here is ") + path + String(":\n\n") + contents
            except:
                print("could not read file:", path)
                continue

        # v1.2: persist the user turn before dispatching so crashes during
        # generation don't lose the prompt.
        _ = sm.save_turn(session_id, sm.HistoryDict("user", line))

        var reply = run_loop(line, ctx, args.model, args.max_new_tokens)
        _ = sm.save_turn(session_id, sm.HistoryDict("assistant", reply))
        _ = repl.render_response(reply)


def main() raises:
    var raw_args = argv_to_list()

    var res = parse_args(raw_args)
    if len(res.error) > 0:
        print("mojopi: error:", res.error)
        print_usage()
        return

    var args = res.args.copy()

    # Environment-variable defaults only apply when the user didn't override.
    var repl = Python.import_module("cli.repl_helper")
    var env_model = String(repl.env_model_default())
    if len(env_model) > 0 and args.model == String("modularai/Llama-3.1-8B-Instruct-GGUF"):
        args.model = env_model
    var env_tokens = Int(py=repl.env_max_new_tokens_default())
    if env_tokens > 0 and args.max_new_tokens == 512:
        args.max_new_tokens = env_tokens

    if res.show_help:
        print_usage()
        return

    if args.mode == String("version"):
        var v = get_max_version()
        print("mojopi", VERSION, "/ max:", v)
        return

    if args.mode == String("print"):
        var prompt = args.prompt.copy()

        if len(prompt) == 0:
            var stdin_text = read_stdin_prompt()
            if len(stdin_text) > 0:
                prompt = stdin_text

        if len(prompt) == 0:
            print("mojopi: error: -p requires a prompt (or pipe from stdin)")
            print_usage()
            return

        try:
            prompt = resolve_prompt(prompt)
        except:
            print("mojopi: error: could not read @file argument")
            return

        var output_mode = args.output_mode.copy()
        if not is_valid_mode(output_mode):
            print("mojopi: error: --mode must be json, rpc, or print")
            return

        try:
            var ctx = _build_context(args)
            var result = run_loop(prompt, ctx, args.model, args.max_new_tokens)
            if output_mode == String("print"):
                print(result)
            else:
                emit_answer(result, output_mode)
        except:
            if output_mode == String("print"):
                print("mojopi: error: agent failed")
            else:
                emit_error(String("agent failed"), output_mode)
        return

    _run_interactive(args)
