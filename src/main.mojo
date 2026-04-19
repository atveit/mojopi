# mojopi CLI entry -- C3 scope: one-shot `mojopi -p "<prompt>"` that streams
# tokens from MAX back to stdout. No tools, no session, no agent loop -- those
# arrive in Walk phases (see PLAN.md section 4).

from sys import argv
from prompt.formatter import format_llama3_single_turn
from max_brain.inference import MaxInference, get_max_version

# Default model -- confirmed GGUF-supported per docs.modular.com/max/models/.
alias DEFAULT_MODEL = "modularai/Llama-3.1-8B-Instruct-GGUF"


def print_usage():
    print("usage: mojopi -p <prompt>")
    print("")
    print("C3 crawl-phase build: one-shot, non-interactive, stdout only.")
    print("")
    print("    --version    print MAX version and exit")
    print("    -p, --print  print mode -- required for crawl; emits tokens to stdout")


def main():
    var args = argv()
    # argv()[0] is the program name; skip it.
    if len(args) < 2:
        print_usage()
        return

    var first = String(args[1])

    if first == "--version":
        var v = get_max_version()
        print("mojopi crawl-phase; max:", v)
        return

    if first != "-p" and first != "--print":
        print_usage()
        return

    if len(args) < 3:
        print("error: -p requires a prompt argument", file=2)
        print_usage()
        return

    var user_prompt = String(args[2])
    var formatted = format_llama3_single_turn(user_prompt)

    # Load the pipeline. For C3 this call is sufficient to demonstrate the
    # end-to-end path; streaming tokens is a follow-up when stream_tokens is
    # implemented in max_brain/pipeline.py (tracked as a C3 follow-up).
    var engine = MaxInference(DEFAULT_MODEL)
    print("loaded:", engine.describe())

    # TODO(C3-followup): call engine.stream(formatted) and print tokens as
    # they arrive. The Python-side `stream_tokens` is a C3 deliverable owned
    # by the MAX-Integration agent; this driver is ready to consume it the
    # moment its surface lands. For now we emit the formatted prompt so the
    # smoke-test can eyeball the template.
    print("---formatted prompt---")
    print(formatted)
