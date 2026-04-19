"""Python helper for grep.mojo — runs ripgrep or grep via subprocess."""
import subprocess


def run_grep(
    pattern: str,
    path: str,
    include: str = "",
    max_matches: int = 100,
    case_insensitive: bool = False,
) -> dict:
    """Search for pattern in path using ripgrep (rg) if available, else grep.

    Returns:
        {'matches': [{'file': str, 'line': int, 'text': str}], 'truncated': bool, 'total': int}
    """
    output = _run_command(pattern, path, include, case_insensitive)
    matches = _parse_output(output)

    total = len(matches)
    truncated = total > max_matches
    return {
        "matches": matches[:max_matches],
        "truncated": truncated,
        "total": total,
    }


def _run_command(
    pattern: str, path: str, include: str, case_insensitive: bool
) -> str:
    # Try ripgrep first
    cmd = ["rg", "--line-number", "--no-heading", "--with-filename"]
    if case_insensitive:
        cmd.append("-i")
    if include:
        cmd += ["--glob", include]
    cmd += [pattern, path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except FileNotFoundError:
        pass

    # Fall back to grep -rn
    cmd2 = ["grep", "-rn", "--include=" + include if include else "-rn"]
    if include:
        cmd2 = ["grep", "-rn", "--include=" + include]
    else:
        cmd2 = ["grep", "-rn"]
    if case_insensitive:
        cmd2.append("-i")
    cmd2 += [pattern, path]

    result = subprocess.run(
        cmd2, capture_output=True, text=True, timeout=30
    )
    return result.stdout


def _parse_output(output: str) -> list:
    """Parse rg/grep output lines of the form  filepath:lineno:text."""
    matches = []
    for raw_line in output.splitlines():
        # Find first colon for file path, second colon for line number
        first = raw_line.find(":")
        if first == -1:
            continue
        second = raw_line.find(":", first + 1)
        if second == -1:
            continue
        file_part = raw_line[:first]
        lineno_part = raw_line[first + 1 : second]
        text_part = raw_line[second + 1 :]
        try:
            lineno = int(lineno_part)
        except ValueError:
            continue
        matches.append({"file": file_part, "line": lineno, "text": text_part})
    return matches
