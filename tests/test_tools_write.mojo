from std.testing import assert_equal, assert_true
from std.python import Python

from coding_agent.tools.write import write_file, WriteResult
from coding_agent.tools.read import read_text


def read_back(path: String) raises -> String:
    var py = Python.import_module("pathlib")
    return String(py.Path(path).read_text(encoding="utf-8"))


def test_write_new_file() raises:
    var path = String("/tmp/mojopi_write_test_new.txt")
    var result = write_file(path, "hello from mojo\n")
    assert_true(result.success)
    assert_equal(result.error, "")
    assert_true(result.bytes_written > 0)
    var content = read_back(path)
    assert_true("hello from mojo" in content)


def test_write_overwrites_existing() raises:
    var path = String("/tmp/mojopi_write_test_overwrite.txt")
    # Write initial content.
    _ = write_file(path, "original content\n")
    # Overwrite.
    var result = write_file(path, "new content\n")
    assert_true(result.success)
    var content = read_back(path)
    assert_true("new content" in content)
    assert_equal("original content\n" in content, False)


def test_write_creates_parent_dirs() raises:
    var path = String("/tmp/mojopi_write_nested/subdir/test.txt")
    var result = write_file(path, "nested file\n", create_parents=True)
    assert_true(result.success)
    var content = read_back(path)
    assert_true("nested file" in content)


def test_write_content_matches_read_back() raises:
    var path = String("/tmp/mojopi_write_test_roundtrip.txt")
    var original = String("line one\nline two\nline three\n")
    _ = write_file(path, original)
    # Use read.mojo's read_text to verify the content round-trips correctly.
    var read_result = read_text(path, 1, 100)
    assert_true("line one" in read_result.content)
    assert_true("line two" in read_result.content)
    assert_true("line three" in read_result.content)
    assert_equal(read_result.truncated, False)


def main() raises:
    test_write_new_file()
    test_write_overwrites_existing()
    test_write_creates_parent_dirs()
    test_write_content_matches_read_back()
    print("All write tests passed!")
