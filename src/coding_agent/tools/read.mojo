# Ports pi-mono/packages/coding-agent/src/core/tools/read.ts — C2 subset.
#
# Scope for C2: text reading with 1-indexed line offset/limit and byte-cap
# truncation. Deferred to later phases: image decoding + MIME detection,
# auto-resize pipeline, SSH/remote `ReadOperations`, AbortSignal threading,
# continuation hints ("[Showing lines X-Y of Z. Use offset=N...]"), TUI
# render helpers, tool-definition wrapping / schema binding, tab replacement,
# syntax highlighting, `firstLineExceedsLimit` bash-fallback text.

from std.collections import List
from std.pathlib import Path


struct ReadResult(Copyable, Movable):
    var content: String
    var truncated: Bool
    var lines_read: Int
    var total_lines: Int

    def __init__(
        out self,
        content: String,
        truncated: Bool,
        lines_read: Int,
        total_lines: Int,
    ):
        self.content = content
        self.truncated = truncated
        self.lines_read = lines_read
        self.total_lines = total_lines


def read_text(
    path: String,
    offset: Int = 1,
    limit: Int = 100,
    max_bytes: Int = 10000,
) raises -> ReadResult:
    """Read a text file with 1-indexed line offset and line limit.

    - `offset`: 1-indexed starting line (default 1 = file start).
    - `limit`: maximum number of lines to return (default 100).
    - `max_bytes`: cap on returned content bytes (default 10_000). If the
      joined slice exceeds this, it is truncated at the last full line and a
      marker `"\\n...{N} lines omitted..."` is appended, where {N} is the
      number of lines dropped relative to the pre-truncation slice.

    Raises if the file does not exist.
    """
    var p = Path(path)
    if not p.exists():
        raise Error(String("read_text: file not found: ") + path)

    var text = p.read_text()

    # Split into lines. Mojo's String.split preserves trailing empty strings
    # (matching TS `split("\n")`), so `total_lines` counts the final empty
    # entry when the file ends in a newline — the same count TS reports.
    var all_lines = text.split("\n")
    var total_lines = len(all_lines)

    # Out-of-range offset — return empty, not an error (PLAN §4 C2 spec).
    if offset > total_lines:
        return ReadResult(String(""), False, 0, total_lines)

    # Slice [offset-1 : offset-1+limit], clamped to available lines.
    var start = offset - 1
    if start < 0:
        start = 0
    var stop = start + limit
    if stop > total_lines:
        stop = total_lines

    # Build the sliced line list. `String.split(sep)` returns StringSlice
    # views into `text`; materialize into owned Strings so downstream code
    # doesn't depend on `text`'s lifetime.
    var sliced = List[String]()
    for i in range(start, stop):
        sliced.append(String(all_lines[i]))
    var sliced_count = len(sliced)

    # Join with '\n'. Manual loop — avoids relying on a specific join API shape.
    var joined = String("")
    for i in range(sliced_count):
        if i > 0:
            joined += "\n"
        joined += sliced[i]

    # Byte-cap check. `len(String)` is byte length in Mojo.
    if len(joined) <= max_bytes:
        return ReadResult(joined^, False, sliced_count, total_lines)

    # Truncate: keep adding lines until the next would overflow.
    var kept = String("")
    var kept_count = 0
    for i in range(sliced_count):
        var next_len: Int
        if kept_count == 0:
            next_len = len(sliced[i])
        else:
            next_len = len(kept) + 1 + len(sliced[i])  # +1 for '\n'
        if next_len > max_bytes:
            break
        if kept_count > 0:
            kept += "\n"
        kept += sliced[i]
        kept_count += 1

    var omitted = sliced_count - kept_count
    kept += "\n..."
    kept += String(omitted)
    kept += " lines omitted..."

    return ReadResult(kept^, True, kept_count, total_lines)
