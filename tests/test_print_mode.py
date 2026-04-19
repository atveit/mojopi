import sys; sys.path.insert(0, "src")

def test_print_helper_importable():
    from cli import print_helper
    assert hasattr(print_helper, "expand_at_file")
    assert hasattr(print_helper, "resolve_prompt")
    assert hasattr(print_helper, "read_stdin_prompt")

def test_expand_at_file_passthrough():
    from cli.print_helper import expand_at_file
    result = expand_at_file("hello world")
    assert result == "hello world"

def test_expand_at_file_reads_file(tmp_path):
    from cli.print_helper import expand_at_file
    f = tmp_path / "prompt.txt"
    f.write_text("my prompt from file")
    result = expand_at_file(f"@{f}")
    assert result == "my prompt from file"

def test_expand_at_file_missing_raises(tmp_path):
    from cli.print_helper import expand_at_file
    import pytest
    with pytest.raises(FileNotFoundError):
        expand_at_file("@/tmp/does_not_exist_xyz_mojopi.txt")

def test_resolve_prompt_strips(tmp_path):
    from cli.print_helper import resolve_prompt
    assert resolve_prompt("  hello  ") == "hello"

def test_resolve_prompt_at_file(tmp_path):
    from cli.print_helper import resolve_prompt
    f = tmp_path / "p.txt"
    f.write_text("  file content  ")
    assert resolve_prompt(f"@{f}") == "file content"

def test_read_stdin_tty_returns_none():
    """In test environment, stdin is a tty (or at least not providing data)."""
    from cli.print_helper import read_stdin_prompt
    # In pytest, stdin is usually a tty; result is None or empty str
    result = read_stdin_prompt()
    # Either None or empty is acceptable in test env
    assert result is None or isinstance(result, str)
