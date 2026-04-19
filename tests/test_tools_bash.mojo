from std.testing import assert_equal, assert_true

from coding_agent.tools.bash import run_bash, BashResult


def test_echo_command() raises:
    var result = run_bash("echo hello")
    assert_equal(result.exit_code, 0)
    assert_true(len(result.stdout) > 0)


def test_exit_code_nonzero() raises:
    var result = run_bash("exit 42", cwd=".")
    assert_equal(result.exit_code, 42)


def test_stderr_captured() raises:
    var result = run_bash("echo err >&2")
    assert_true(len(result.stderr) > 0)


def test_stdout_content() raises:
    var result = run_bash("echo mojopi")
    assert_true("mojopi" in result.stdout)
    assert_equal(result.exit_code, 0)


def test_timed_out_false_on_fast_command() raises:
    var result = run_bash("echo fast")
    assert_equal(result.timed_out, False)


def main() raises:
    test_echo_command()
    test_exit_code_nonzero()
    test_stderr_captured()
    test_stdout_content()
    test_timed_out_false_on_fast_command()
    print("All bash tests passed!")
