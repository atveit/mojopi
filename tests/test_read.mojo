from std.testing import assert_equal, assert_true, assert_false

from coding_agent.tools.read import read_text


def test_read_full_fifty_line_file() raises:
    var result = read_text("tests/fixtures/fifty_lines.txt")
    assert_equal(result.total_lines, 50)
    assert_equal(result.lines_read, 50)
    assert_false(result.truncated)


def test_read_with_offset_and_limit() raises:
    # Read lines 10..14 inclusive (1-indexed offset=10, limit=5 → lines 10,11,12,13,14)
    var result = read_text("tests/fixtures/fifty_lines.txt", 10, 5)
    assert_equal(result.lines_read, 5)
    assert_true("line 10" in result.content)
    assert_true("line 14" in result.content)
    assert_false("line 9" in result.content)
    assert_false("line 15" in result.content)


def test_read_beyond_eof_is_graceful() raises:
    var result = read_text("tests/fixtures/fifty_lines.txt", 100, 5)
    assert_equal(result.lines_read, 0)
    assert_equal(result.total_lines, 50)


def test_read_small_file() raises:
    var result = read_text("tests/fixtures/five_lines.txt")
    assert_equal(result.total_lines, 5)
    assert_equal(result.lines_read, 5)


def test_truncation_marker_on_byte_cap() raises:
    # Force truncation by setting a very small byte cap.
    var result = read_text("tests/fixtures/fifty_lines.txt", 1, 100, 20)
    assert_true(result.truncated)
    assert_true("lines omitted" in result.content)
