"""Python helper for find.mojo — walks a directory tree via pathlib."""
from pathlib import Path


_DEFAULT_EXCLUDE = [".git", "node_modules", "__pycache__", ".pixi"]


def run_find(
    directory: str,
    pattern: str = "*",
    file_type: str = "",
    max_results: int = 100,
    exclude_dirs: list = None,
) -> dict:
    """Find files/dirs matching pattern under directory.

    Returns:
        {'paths': [str, ...], 'truncated': bool, 'total': int}
    """
    if exclude_dirs is None:
        exclude_dirs = _DEFAULT_EXCLUDE

    root = Path(directory)
    results = []

    for p in root.rglob(pattern):
        # Skip if any path component is in the exclude list
        if any(part in exclude_dirs for part in p.parts):
            continue
        if file_type == "f" and not p.is_file():
            continue
        if file_type == "d" and not p.is_dir():
            continue
        results.append(str(p))
        if len(results) > max_results:
            return {
                "paths": results[:max_results],
                "truncated": True,
                "total": len(results),
            }

    return {"paths": results, "truncated": False, "total": len(results)}
