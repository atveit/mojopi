# Ports pi-mono/packages/coding-agent/src/core/session-manager.ts schema v3.
# All 7 entry types as Mojo structs.  Each struct:
#   - implements (Copyable, Movable)
#   - uses `self.field = field.copy()` for every String param (PLAN §0 C1 rule:
#     def params are immutable refs; ^ transfer fails; .copy() is canonical)
#   - uses `out self` in __init__ (current Mojo constructor convention)
#
# JSON ↔ struct conversion is handled in Python (store.py); these structs hold
# the in-process representation after parsing.


# ---------------------------------------------------------------------------
# SessionHeader — type: "session"
# First entry in every JSONL file; parentId is always null (represented here
# as empty string).
# ---------------------------------------------------------------------------
struct SessionHeader(Copyable, Movable):
    var id: String
    var parent_id: String  # empty string = null
    var cwd: String
    var timestamp: Int64
    var version: Int  # always 3

    def __init__(
        out self,
        id: String,
        parent_id: String,
        cwd: String,
        timestamp: Int64,
        version: Int,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.cwd = cwd.copy()
        self.timestamp = timestamp
        self.version = version


# ---------------------------------------------------------------------------
# MessageEntry — type: "message"
# Carries a full agent message (user / assistant / tool_result).
# `content_json` holds the raw JSON of the message object so we don't need
# to model every variant here — the Python layer serialises/deserialises it.
# ---------------------------------------------------------------------------
struct MessageEntry(Copyable, Movable):
    var id: String
    var parent_id: String
    var role: String        # "user", "assistant", "tool_result"
    var content_json: String  # raw JSON of message content

    def __init__(
        out self,
        id: String,
        parent_id: String,
        role: String,
        content_json: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.role = role.copy()
        self.content_json = content_json.copy()


# ---------------------------------------------------------------------------
# ThinkingLevelChange — type: "thinking_level_change"
# ---------------------------------------------------------------------------
struct ThinkingLevelChange(Copyable, Movable):
    var id: String
    var parent_id: String
    var level: String  # "none", "normal", "deep"

    def __init__(
        out self,
        id: String,
        parent_id: String,
        level: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.level = level.copy()


# ---------------------------------------------------------------------------
# ModelChange — type: "model_change"
# ---------------------------------------------------------------------------
struct ModelChange(Copyable, Movable):
    var id: String
    var parent_id: String
    var model: String

    def __init__(
        out self,
        id: String,
        parent_id: String,
        model: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.model = model.copy()


# ---------------------------------------------------------------------------
# CompactionEntry — type: "compaction"
# ---------------------------------------------------------------------------
struct CompactionEntry(Copyable, Movable):
    var id: String
    var parent_id: String
    var summary: String
    var token_count: Int

    def __init__(
        out self,
        id: String,
        parent_id: String,
        summary: String,
        token_count: Int,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.summary = summary.copy()
        self.token_count = token_count


# ---------------------------------------------------------------------------
# BranchSummaryEntry — type: "branch_summary"
# ---------------------------------------------------------------------------
struct BranchSummaryEntry(Copyable, Movable):
    var id: String
    var parent_id: String
    var label: String

    def __init__(
        out self,
        id: String,
        parent_id: String,
        label: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.label = label.copy()


# ---------------------------------------------------------------------------
# CustomEntry — type: "custom"
# Extension state; data stored as raw JSON string.
# ---------------------------------------------------------------------------
struct CustomEntry(Copyable, Movable):
    var id: String
    var parent_id: String
    var data_json: String  # raw JSON

    def __init__(
        out self,
        id: String,
        parent_id: String,
        data_json: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.data_json = data_json.copy()


# ---------------------------------------------------------------------------
# CustomMessageEntry — type: "custom_message"
# Injected message; message stored as raw JSON string.
# ---------------------------------------------------------------------------
struct CustomMessageEntry(Copyable, Movable):
    var id: String
    var parent_id: String
    var message_json: String  # raw JSON

    def __init__(
        out self,
        id: String,
        parent_id: String,
        message_json: String,
    ):
        self.id = id.copy()
        self.parent_id = parent_id.copy()
        self.message_json = message_json.copy()
