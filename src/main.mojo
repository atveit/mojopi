from std.sys import argv
from std.python import Python

from cli.args import parse_args, argv_to_list, CliArgs, ParseResult
from cli.print_helper import resolve_prompt, read_stdin_prompt
from max_brain.inference import generate_embedded, run_one_shot, get_max_version
from agent.output_mode import emit_answer, emit_error, is_valid_mode

comptime VERSION = "0.1.0-walk"

def print_usage():
    print("usage: mojopi [options]")
    print("")
    print("  -p, --print <prompt>     one-shot mode: generate and print to stdout")
    print("  --version                print version and exit")
    print("  --model <hf-repo>        model repo (default: modularai/Llama-3.1-8B-Instruct-GGUF)")
    print("  --max-new-tokens N       token cap (default: 512)")
    print("  --session <id>           resume session by uuid prefix or path")
    print("  --no-context-files       skip AGENTS.md / CLAUDE.md context loading")
    print("  --tools t1,t2            restrict to named tools")
    print("  --no-tools               disable all tool use")
    print("  --system-prompt <text>   override system prompt")
    print("  --append-system-prompt <text>  append to system prompt")
    print("  --verbose / -v           verbose output")
    print("")
    print("  Prompt can be @filepath to read from file.")


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

        # Stdin piping: if prompt is empty and stdin has data, read from stdin.
        if len(prompt) == 0:
            var stdin_text = read_stdin_prompt()
            if len(stdin_text) > 0:
                prompt = stdin_text

        if len(prompt) == 0:
            print("mojopi: error: -p requires a prompt (or pipe from stdin)")
            print_usage()
            return

        # @file expansion
        try:
            prompt = resolve_prompt(prompt)
        except:
            print("mojopi: error: could not read @file argument")
            return

        # Apply system prompt overrides (context available for future use)
        var _ = args.system_prompt_override.copy()
        var _ = args.append_system_prompt.copy()

        # Validate output mode
        var output_mode = args.output_mode.copy()
        if not is_valid_mode(output_mode):
            print("mojopi: error: --mode must be json, rpc, or print")
            return

        # Generate
        var model = args.model.copy()
        var max_new = args.max_new_tokens

        try:
            var result = generate_embedded(prompt, model, max_new)
            if output_mode == String("print"):
                print(result)
            else:
                emit_answer(result, output_mode)
        except:
            if output_mode == String("print"):
                var rc = run_one_shot(prompt, model, max_new)
                if rc != 0:
                    print("(generate exited with code", rc, ")")
            else:
                emit_error(String("generation failed"), output_mode)
        return

    # Interactive mode — not yet implemented in R1
    print("mojopi: interactive mode is not yet implemented (use -p for print mode)")
