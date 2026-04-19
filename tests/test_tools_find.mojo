from std.testing import assert_equal, assert_true, assert_false
from std.collections import List

from coding_agent.tools.find import find_files, FindResult


def test_find_all_in_fixtures() raises:
    var result = find_files("tests/fixtures")
    assert_true(result.total_found > 0, "should find files in tests/fixtures")
    assert_false(result.truncated, "small fixture dir should not truncate")


def test_find_txt_files_only() raises:
    var result = find_files("tests/fixtures", pattern="*.txt")
    assert_true(result.total_found > 0, "should find .txt files")
    # All returned paths should end in .txt
    for i in range(len(result.paths)):
        var p = result.paths[i]
        assert_true(p.endswith(".txt"), "expected .txt path, got: " + p)


def test_find_files_type_f() raises:
    var result = find_files("tests/fixtures", file_type="f")
    assert_true(result.total_found > 0, "should find files with type=f")
    assert_true(len(result.paths) > 0, "paths list should be non-empty")


def test_find_truncation() raises:
    # max_results=1 with multiple files → truncated
    var result = find_files("tests/fixtures", max_results=1)
    assert_equal(len(result.paths), 1)
    assert_true(result.truncated, "should truncate when more results than max_results")


def test_find_nonexistent_dir() raises:
    # A non-existent dir: verify that an error is raised or empty result returned cleanly.
    var raised = False
    try:
        _ = find_files("tests/fixtures/does_not_exist_xyz")
    except:
        raised = True
    _ = raised  # Either outcome is acceptable; test just verifies no crash


def main() raises:
    test_find_all_in_fixtures()
    test_find_txt_files_only()
    test_find_files_type_f()
    test_find_truncation()
    test_find_nonexistent_dir()
    print("All find tests passed!")
