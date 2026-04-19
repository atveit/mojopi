"""bash_tool.py — run a shell command with timeout and SIGTERM on the process group.

Port of pi-mono/packages/coding-agent/src/core/tools/bash.ts — C2 subset.
"""


def run_bash(
    command: str,
    cwd: str = ".",
    timeout: float = 30.0,  # seconds; 0 = no timeout
    max_output_bytes: int = 100_000,
) -> dict:
    """Run a shell command. Returns:
    {
      'stdout': str,
      'stderr': str,
      'exit_code': int,
      'timed_out': bool,
      'truncated': bool,
    }
    Sends SIGTERM to the child process tree on timeout.
    Captures stdout and stderr separately.
    """
    import os
    import signal
    import subprocess

    effective_timeout = timeout if timeout > 0 else None

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # new process group → clean SIGTERM
        )
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=effective_timeout)
            timed_out = False
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            # Kill the entire process group so child processes are also reaped.
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass  # process already gone
            stdout_bytes, stderr_bytes = proc.communicate()
            timed_out = True
            exit_code = 124  # matches bash `timeout` convention
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": 1,
            "timed_out": False,
            "truncated": False,
        }

    stdout_str = stdout_bytes.decode("utf-8", errors="replace")
    stderr_str = stderr_bytes.decode("utf-8", errors="replace")

    # Truncate combined output if it exceeds max_output_bytes.
    truncated = False
    total_len = len(stdout_str.encode("utf-8")) + len(stderr_str.encode("utf-8"))
    if total_len > max_output_bytes:
        truncated = True
        # Allocate proportionally; give stdout the majority.
        stdout_share = int(max_output_bytes * 0.7)
        stderr_share = max_output_bytes - stdout_share
        stdout_str = stdout_str[:stdout_share]
        stderr_str = stderr_str[:stderr_share]

    return {
        "stdout": stdout_str,
        "stderr": stderr_str,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "truncated": truncated,
    }
