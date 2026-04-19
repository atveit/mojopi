from std.testing import assert_equal, assert_true, assert_false

from coding_agent.tools.ls import ls_directory, LsResult, LsEntry


def test_ls_fixtures_returns_entries() raises:
    var result = ls_directory("tests/fixtures")
    assert_true(len(result.entries) > 0, "should have entries in tests/fixtures")


def test_ls_path_field() raises:
    var result = ls_directory("tests/fixtures")
    assert_equal(result.path, "tests/fixtures")


def test_ls_dirs_before_files() raises:
    # tests/fixtures contains the fake_project subdirectory and .txt files.
    # Dirs must appear before files.
    var result = ls_directory("tests/fixtures")
    var seen_file = False
    for i in range(len(result.entries)):
        var e = result.entries[i].copy()
        if seen_file:
            assert_false(e.is_dir, "directory appeared after a file — sort order wrong")
        if not e.is_dir:
            seen_file = True


def test_ls_hidden_excluded_by_default() raises:
    var result = ls_directory("tests/fixtures")
    for i in range(len(result.entries)):
        var name = result.entries[i].copy().name
        assert_false(
            name.startswith("."),
            "hidden entry should not appear when show_hidden=False: " + name,
        )


def test_ls_size_and_mtime_populated() raises:
    var result = ls_directory("tests/fixtures")
    # At least one file entry should have size > 0
    var found_nonzero = False
    for i in range(len(result.entries)):
        var e = result.entries[i].copy()
        if not e.is_dir and e.size_bytes > 0:
            found_nonzero = True
    assert_true(found_nonzero, "at least one file should have size_bytes > 0")


def main() raises:
    test_ls_fixtures_returns_entries()
    test_ls_path_field()
    test_ls_dirs_before_files()
    test_ls_hidden_excluded_by_default()
    test_ls_size_and_mtime_populated()
    print("All ls tests passed!")
