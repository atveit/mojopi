"""edit_helper.py — targeted string-replacement edit on a file.

Port of pi-mono/packages/coding-agent/src/core/tools/edit.ts — C2 subset.
"""


def apply_edit(
    file_path: str,
    old_string: str,
    new_string: str,
) -> dict:
    """Replace first occurrence of old_string with new_string in file_path.

    Returns:
    {
      'success': bool,
      'error': str or None,   # "not found", "ambiguous" (multiple matches),
                               # "file not found"
      'match_count': int,
    }
    Fails if old_string appears 0 times (not found) or more than 1 time
    (ambiguous).  On success, writes the modified content back to the file.
    """
    from pathlib import Path

    p = Path(file_path)
    if not p.exists():
        return {"success": False, "error": "file not found", "match_count": 0}

    content = p.read_text(encoding="utf-8")
    count = content.count(old_string)

    if count == 0:
        return {"success": False, "error": "not found", "match_count": 0}
    if count > 1:
        return {"success": False, "error": "ambiguous", "match_count": count}

    p.write_text(content.replace(old_string, new_string, 1), encoding="utf-8")
    return {"success": True, "error": None, "match_count": 1}
