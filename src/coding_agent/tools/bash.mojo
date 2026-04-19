# Ports pi-mono/packages/coding-agent/src/core/tools/bash.ts — C2 subset.
#
# Scope for C2: shell command execution with timeout, SIGTERM on process group,
# and byte-cap truncation. Delegates to bash_tool.py via Python interop.

from std.python import Python, PythonObject


struct BashResult(Copyable, Movable):
    var stdout: String
    var stderr: String
    var exit_code: Int
    var timed_out: Bool
    var truncated: Bool

    def __init__(
        out self,
        stdout: String,
        stderr: String,
        exit_code: Int,
        timed_out: Bool,
        truncated: Bool,
    ):
        self.stdout = stdout.copy()
        self.stderr = stderr.copy()
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.truncated = truncated


def run_bash(
    command: String,
    cwd: String = ".",
    timeout_seconds: Float64 = 30.0,
    max_output_bytes: Int = 100000,
) raises -> BashResult:
    """Run a shell command via Python subprocess.

    Returns a BashResult with stdout, stderr, exit_code, timed_out, and
    truncated fields.  Exit code 124 signals a timeout (matches bash
    `timeout` convention).
    """
    var mod = Python.import_module("coding_agent.tools.bash_tool")
    var result = mod.run_bash(command, cwd, timeout_seconds, max_output_bytes)
    return BashResult(
        String(result["stdout"]),
        String(result["stderr"]),
        Int(py=result["exit_code"]),
        Bool(result["timed_out"]),
        Bool(result["truncated"]),
    )
