from std.testing import assert_equal, assert_true, assert_false
from std.python import Python

from coding_agent.tools.edit import apply_edit, EditResult


def write_temp(path: String, content: String) raises:
    var py = Python.import_module("pathlib")
    py.Path(path).write_text(content, encoding="utf-8")


def read_temp(path: String) raises -> String:
    var py = Python.import_module("pathlib")
    return String(py.Path(path).read_text(encoding="utf-8"))


def test_edit_success() raises:
    var path = String("/tmp/mojopi_edit_test_success.txt")
    write_temp(path, "hello world\ngoodbye world\n")
    var result = apply_edit(path, "hello world", "hi world")
    assert_true(result.success)
    assert_equal(result.error, "")
    assert_equal(result.match_count, 1)
    var content = read_temp(path)
    assert_true("hi world" in content)
    assert_false("hello world" in content)


def test_edit_not_found() raises:
    var path = String("/tmp/mojopi_edit_test_not_found.txt")
    write_temp(path, "hello world\n")
    var result = apply_edit(path, "nonexistent string", "replacement")
    assert_false(result.success)
    assert_equal(result.error, "not found")
    assert_equal(result.match_count, 0)


def test_edit_ambiguous() raises:
    var path = String("/tmp/mojopi_edit_test_ambiguous.txt")
    write_temp(path, "foo\nfoo\n")
    var result = apply_edit(path, "foo", "bar")
    assert_false(result.success)
    assert_equal(result.error, "ambiguous")
    assert_equal(result.match_count, 2)


def test_edit_file_not_found() raises:
    var result = apply_edit(
        "/tmp/mojopi_nonexistent_file_xyz.txt",
        "anything",
        "replacement",
    )
    assert_false(result.success)
    assert_equal(result.error, "file not found")
    assert_equal(result.match_count, 0)


def main() raises:
    test_edit_success()
    test_edit_not_found()
    test_edit_ambiguous()
    test_edit_file_not_found()
    print("All edit tests passed!")
