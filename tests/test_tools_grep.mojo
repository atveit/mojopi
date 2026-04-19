from std.testing import assert_equal, assert_true

from coding_agent.tools.grep import grep_text, GrepResult, GrepMatch


def test_grep_finds_pattern() raises:
    var result = grep_text("hello", "tests/fixtures/grep_sample.txt")
    assert_true(result.total_matches > 0, "should find 'hello'")


def test_grep_no_match() raises:
    var result = grep_text("xyz_not_in_file_xyz123456", "tests/fixtures/grep_sample.txt")
    assert_equal(result.total_matches, 0)


def test_grep_case_insensitive() raises:
    var result = grep_text("HELLO", "tests/fixtures/grep_sample.txt", case_insensitive=True)
    assert_true(result.total_matches > 0, "case-insensitive search should find 'hello' lines")


def test_grep_match_fields() raises:
    var result = grep_text("hello", "tests/fixtures/grep_sample.txt")
    assert_true(result.total_matches > 0, "should have matches")
    # First match should be on line 1
    var first = result.matches[0].copy()
    assert_equal(first.line_number, 1)
    assert_true("hello" in first.line, "match text should contain the pattern")


def test_grep_truncation() raises:
    # max_matches=1 on a file with multiple matching lines → truncated
    var result = grep_text("hello", "tests/fixtures/grep_sample.txt", max_matches=1, case_insensitive=True)
    assert_equal(len(result.matches), 1)
    assert_true(result.truncated, "should be truncated when more matches exist than max")


def main() raises:
    test_grep_finds_pattern()
    test_grep_no_match()
    test_grep_case_insensitive()
    test_grep_match_fields()
    test_grep_truncation()
    print("All grep tests passed!")
