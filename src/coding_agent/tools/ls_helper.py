"""Python helper for ls.mojo — lists a directory via os.scandir."""
import os


def run_ls(path: str, show_hidden: bool = False) -> dict:
    """List directory contents, sorted dirs-first then alphabetical.

    Returns:
        {'entries': [{'name': str, 'is_dir': bool, 'size': int, 'mtime': int}], 'path': str}
    """
    entries = []
    with os.scandir(path) as it:
        items = list(it)

    # Sort: dirs first (is_dir=False sorts after True with `not`), then name
    items.sort(key=lambda e: (not e.is_dir(), e.name.lower()))

    for entry in items:
        if not show_hidden and entry.name.startswith("."):
            continue
        s = entry.stat()
        entries.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": s.st_size,
                "mtime": int(s.st_mtime),
            }
        )

    return {"entries": entries, "path": path}
