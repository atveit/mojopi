# CLI argument parser for mojopi.
# Parses the full mojopi CLI surface; main.mojo can import from this module.

from std.sys import argv
from std.collections import List

# Run mode constants.
comptime MODE_PRINT = "print"
comptime MODE_INTERACTIVE = "interactive"
comptime MODE_VERSION = "version"


struct CliArgs(Copyable, Movable):
    """Parsed CLI arguments for mojopi."""

    # Core mode
    var mode: String        # "print", "interactive", or "version"
    var prompt: String      # -p / --print <prompt> (empty if not print mode)

    # Model config
    var model: String           # --model <hf-repo>
    var max_new_tokens: Int     # --max-new-tokens N

    # Session
    var session: String         # --session <uuid-prefix|path> (empty = new session)

    # Context files
    var no_context_files: Bool          # --no-context-files
    var system_prompt_override: String  # --system-prompt <text>
    var append_system_prompt: String    # --append-system-prompt <text>

    # Tool control
    var tools: List[String]     # --tools tool1,tool2 (empty = all tools)
    var no_tools: Bool          # --no-tools

    # Structured output
    var enable_structured_output: Bool  # --enable-structured-output (GPU only)

    # Debug
    var verbose: Bool           # --verbose / -v

    def __init__(out self):
        self.mode = String(MODE_INTERACTIVE)
        self.prompt = String("")
        self.model = String("modularai/Llama-3.1-8B-Instruct-GGUF")
        self.max_new_tokens = 512
        self.session = String("")
        self.no_context_files = False
        self.system_prompt_override = String("")
        self.append_system_prompt = String("")
        self.tools = List[String]()
        self.no_tools = False
        self.enable_structured_output = False
        self.verbose = False


struct ParseResult(Copyable, Movable):
    """Result of parsing CLI args; check error field before using args."""

    var args: CliArgs
    var error: String       # empty = success
    var show_help: Bool

    def __init__(out self, var args: CliArgs, error: String, show_help: Bool):
        self.args = args^
        self.error = error.copy()
        self.show_help = show_help


def parse_args(raw_args: List[String]) raises -> ParseResult:
    """Parse a list of string arguments into CliArgs.

    raw_args should be the CLI args AFTER stripping argv[0] (the script path)
    and stripping the "--" separator that mojo run inserts.

    Returns ParseResult with error non-empty on parse failure.
    """
    var result = CliArgs()
    var show_help = False
    var i = 0

    while i < len(raw_args):
        var flag = raw_args[i]

        if flag == String("--help") or flag == String("-h"):
            show_help = True
            i += 1

        elif flag == String("--version"):
            result.mode = String(MODE_VERSION)
            i += 1

        elif flag == String("-p") or flag == String("--print"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("-p / --print requires a prompt argument"),
                    show_help,
                )
            result.mode = String(MODE_PRINT)
            result.prompt = raw_args[i + 1].copy()
            i += 2

        elif flag == String("--model"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--model requires an argument"),
                    show_help,
                )
            result.model = raw_args[i + 1].copy()
            i += 2

        elif flag == String("--max-new-tokens"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--max-new-tokens requires an argument"),
                    show_help,
                )
            result.max_new_tokens = Int(raw_args[i + 1])
            i += 2

        elif flag == String("--session"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--session requires an argument"),
                    show_help,
                )
            result.session = raw_args[i + 1].copy()
            i += 2

        elif flag == String("--no-context-files"):
            result.no_context_files = True
            i += 1

        elif flag == String("--system-prompt"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--system-prompt requires an argument"),
                    show_help,
                )
            result.system_prompt_override = raw_args[i + 1].copy()
            i += 2

        elif flag == String("--append-system-prompt"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--append-system-prompt requires an argument"),
                    show_help,
                )
            result.append_system_prompt = raw_args[i + 1].copy()
            i += 2

        elif flag == String("--tools"):
            if i + 1 >= len(raw_args):
                return ParseResult(
                    result^,
                    String("--tools requires an argument"),
                    show_help,
                )
            var tools_str = raw_args[i + 1].copy()
            var parts = tools_str.split(",")
            for j in range(len(parts)):
                result.tools.append(String(parts[j]))
            i += 2

        elif flag == String("--no-tools"):
            result.no_tools = True
            i += 1

        elif flag == String("--enable-structured-output"):
            result.enable_structured_output = True
            i += 1

        elif flag == String("--verbose") or flag == String("-v"):
            result.verbose = True
            i += 1

        else:
            return ParseResult(
                result^,
                String("unknown flag: ") + flag,
                show_help,
            )

    return ParseResult(result^, String(""), show_help)


def usage_string() raises -> String:
    """Return the full usage string (no print, just return)."""
    return (
        "usage: mojopi [-p <prompt>] [options]\n"
        "\n"
        "  --version                      print version and exit\n"
        "  -p, --print <prompt>           one-shot print mode: run prompt and exit\n"
        "  --model <hf-repo>              HuggingFace model repo"
        " (default: modularai/Llama-3.1-8B-Instruct-GGUF)\n"
        "  --max-new-tokens N             cap on tokens to generate (default: 512)\n"
        "  --session <uuid-prefix|path>   resume a previous session\n"
        "  --no-context-files             skip loading context files\n"
        "  --system-prompt <text>         override the system prompt\n"
        "  --append-system-prompt <text>  append text to the system prompt\n"
        "  --tools <tool1,tool2,...>       restrict to named tools (default: all)\n"
        "  --no-tools                     disable all tools\n"
        "  --verbose, -v                  enable verbose debug output\n"
        "  --help, -h                     show this help message\n"
    )


def argv_to_list() raises -> List[String]:
    """Read sys.argv(), skip the script path and '--' separator, return as List[String]."""
    var raw = argv()
    var result = List[String]()
    var skip_first = True
    for i in range(len(raw)):
        if skip_first:
            skip_first = False
            continue
        var s = String(raw[i])
        if s == String("--") and len(result) == 0:
            continue  # skip the mojo run '--' separator
        result.append(s)
    return result^
