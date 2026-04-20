from std.sys import argv
from std.python import Python
from std.collections import List

from cli.args import parse_args, argv_to_list, CliArgs, ParseResult
from cli.print_helper import resolve_prompt, read_stdin_prompt
from max_brain.inference import get_max_version
from agent.types import AgentContext, HistoryEntry, AgentTool
from agent.loop import run_loop
from agent.output_mode import emit_answer, emit_error, is_valid_mode

comptime VERSION = "1.0.0-rc"


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


def _run_interactive(args: CliArgs) raises:
    print("mojopi", VERSION, "— interactive mode. Type /exit to quit, /help for commands.")
    var builtins = Python.import_module("builtins")
    var ctx = _build_context(args)

    while True:
        print("")
        var line = String(builtins.input("> "))
        var stripped = line.strip()
        if len(stripped) == 0:
            continue
        if stripped == "/exit" or stripped == "/quit":
            return
        if stripped == "/help":
            print("  /exit, /quit       exit")
            print("  /clear             clear screen")
            print("  /version           print version")
            print("  anything else      send to agent")
            continue
        if stripped == "/clear":
            print("\033[2J\033[H")
            continue
        if stripped == "/version":
            var v = get_max_version()
            print("mojopi", VERSION, "/ max:", v)
            continue

        var reply = run_loop(line, ctx, args.model, args.max_new_tokens)
        print(reply)


def main() raises:
    var raw_args = argv_to_list()

    var res = parse_args(raw_args)
    if len(res.error) > 0:
        print("mojopi: error:", res.error)
        print_usage()
        return

    var args = res.args.copy()

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
