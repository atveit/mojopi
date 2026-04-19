# mojopi CLI entry -- C3 scope: one-shot `mojopi -p "<prompt>"` that streams
# tokens from MAX back to stdout. No tools, no session, no agent loop -- those
# arrive in Walk phases (see PLAN.md section 4).

from std.sys import argv
from prompt.formatter import format_llama3_single_turn
from max_brain.inference import get_max_version, run_one_shot

# Default model: Modular's published Llama-3.1-8B Q4_K_M GGUF. This is
# MAX 26.2's reference model (CPU-compatible via Q4_K). A smaller model
# would be nice for smoke but the MAX 26.2 Apple-GPU topk constraint
# means CPU is mandatory on arm64, and no smaller text model in the
# supported-architectures list ships with CPU-compatible quant weights.
comptime DEFAULT_MODEL = "modularai/Llama-3.1-8B-Instruct-GGUF"
comptime DEFAULT_MAX_NEW_TOKENS = 64


def print_usage():
    print("usage: mojopi -p <prompt> [--model <hf-repo>] [--max-new-tokens N]")
    print("")
    print("C3 crawl-phase build: one-shot, non-interactive, stdout only.")
    print("")
    print("    --version          print MAX version and exit")
    print("    -p, --print        print mode — emits tokens to stdout")
    print("    --model <repo>     override the default HF model repo")
    print("    --max-new-tokens N cap on tokens to generate (default 64)")
    print("")
    print("default model:", DEFAULT_MODEL)


def main() raises:
    var args = argv()
    # argv()[0] is the Mojo script path. When invoked via `mojo run script -- …`,
    # argv()[1] is the literal "--" separator — skip it if present so user
    # flags start at a consistent index.
    var arg0 = 1
    if len(args) >= 2 and String(args[1]) == "--":
        arg0 = 2

    if len(args) <= arg0:
        print_usage()
        return

    var first = String(args[arg0])

    if first == "--version":
        var v = get_max_version()
        print("mojopi crawl-phase; max:", v)
        return

    if first != "-p" and first != "--print":
        print_usage()
        return

    if len(args) <= arg0 + 1:
        # Mojo's print() has no `file=` kwarg; stderr routing is a W-phase concern.
        print("error: -p requires a prompt argument")
        print_usage()
        return

    # Parse optional flags after the prompt: --model <repo>, --max-new-tokens N.
    # (Minimal arg parsing — a real argparse equivalent lands in R1.)
    var user_prompt = String(args[arg0 + 1])
    var model = String(DEFAULT_MODEL)
    var max_new = DEFAULT_MAX_NEW_TOKENS
    var i = arg0 + 2
    while i < len(args):
        var flag = String(args[i])
        if flag == "--model" and i + 1 < len(args):
            model = String(args[i + 1])
            i += 2
        elif flag == "--max-new-tokens" and i + 1 < len(args):
            max_new = Int(String(args[i + 1]))
            i += 2
        else:
            print("error: unknown or incomplete flag:", flag)
            print_usage()
            return

    # Format as Llama-3 ChatML. Note this template is Llama-3-specific;
    # Qwen/Gemma models ignore the header tokens as regular text but still
    # respond. W2 introduces per-model prompt formatting.
    var formatted = format_llama3_single_turn(user_prompt)

    var rc = run_one_shot(formatted, model, max_new)
    if rc != 0:
        print("(max generate exited with code", rc, ")")
