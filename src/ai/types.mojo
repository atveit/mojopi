from collections import List


# Ports pi-mono/packages/ai/src/types.ts TextContent { type: "text"; text: string }.
struct TextContent(Copyable, Movable):
    var text: String

    def __init__(out self, text: String):
        self.text = text


# Ports pi-mono types.ts ImageContent { type: "image"; data: string; mimeType: string }.
# Mojo field is `mime` (TS `mimeType`) — short form matches the PLAN §3 spec.
struct ImageContent(Copyable, Movable):
    var data: String
    var mime: String

    def __init__(out self, data: String, mime: String):
        self.data = data
        self.mime = mime


# Ports pi-mono types.ts ThinkingContent { type: "thinking"; thinking: string; ... }.
# Field renamed `thinking` -> `text` to match PLAN §3; `signature` is TS `thinkingSignature`.
struct ThinkingContent(Copyable, Movable):
    var text: String
    var redacted: Bool
    var signature: String

    def __init__(out self, text: String, redacted: Bool, signature: String):
        self.text = text
        self.redacted = redacted
        self.signature = signature


# Ports pi-mono types.ts ToolCall { type: "toolCall"; id; name; arguments }.
# `arguments` stored as raw JSON string; validated at dispatch time (W2).
struct ToolCall(Copyable, Movable):
    var id: String
    var name: String
    var arguments: String

    def __init__(out self, id: String, name: String, arguments: String):
        self.id = id
        self.name = name
        self.arguments = arguments


# Ports pi-mono types.ts Usage. Fields renamed to snake_case for Mojo idiom;
# TS `input`/`output` widened to `input_tokens`/`output_tokens` for clarity.
struct Usage(Copyable, Movable):
    var input_tokens: Int
    var output_tokens: Int
    var cache_read_tokens: Int
    var cache_write_tokens: Int
    var total_tokens: Int

    def __init__(
        out self,
        input_tokens: Int,
        output_tokens: Int,
        cache_read_tokens: Int,
        cache_write_tokens: Int,
        total_tokens: Int,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_tokens = cache_read_tokens
        self.cache_write_tokens = cache_write_tokens
        self.total_tokens = total_tokens


# Ports pi-mono types.ts StopReason union "stop" | "length" | "toolUse" | "error" | "aborted".
# Represented as a tagged String wrapper — keeps session-file forward compat trivial.
struct StopReason(Copyable, Movable):
    var value: String

    def __init__(out self, value: String):
        self.value = value


# Ports pi-mono types.ts UserMessage. C2: content is text-only;
# image support deferred to W2 (Variant[TextContent, ImageContent]).
struct UserMessage(Copyable, Movable):
    var content: List[TextContent]
    var timestamp: Int64

    def __init__(out self, content: List[TextContent], timestamp: Int64):
        self.content = content
        self.timestamp = timestamp


# Ports pi-mono types.ts AssistantMessage. C2: text blocks only;
# ThinkingContent/ToolCall blocks deferred to W2 (AssistantBlock variant).
# Dropped fields for C2: api, provider, responseId, errorMessage — not needed
# for the single MAX backend and surface error-via-StopReason handling.
struct AssistantMessage(Copyable, Movable):
    var content: List[TextContent]
    var model: String
    var usage: Usage
    var stop_reason: StopReason
    var timestamp: Int64

    def __init__(
        out self,
        content: List[TextContent],
        model: String,
        usage: Usage,
        stop_reason: StopReason,
        timestamp: Int64,
    ):
        self.content = content
        self.model = model
        self.usage = usage
        self.stop_reason = stop_reason
        self.timestamp = timestamp


# Ports pi-mono types.ts ToolResultMessage. C2: content is text-only;
# image support + `details` payload deferred to W2.
struct ToolResultMessage(Copyable, Movable):
    var tool_call_id: String
    var tool_name: String
    var content: List[TextContent]
    var is_error: Bool
    var timestamp: Int64

    def __init__(
        out self,
        tool_call_id: String,
        tool_name: String,
        content: List[TextContent],
        is_error: Bool,
        timestamp: Int64,
    ):
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.content = content
        self.is_error = is_error
        self.timestamp = timestamp
