from std.collections import List
from ai.types import TextContent, ToolCall, UserMessage, AssistantMessage, ToolResultMessage

# A registered tool that the agent can call.
# W2 scope: text input/output only. Image tools are W3.
struct AgentTool(Copyable, Movable):
    var name: String
    var description: String
    var input_schema_json: String  # JSON Schema string for the tool's input

    def __init__(out self, name: String, description: String, input_schema_json: String):
        self.name = name.copy()
        self.description = description.copy()
        self.input_schema_json = input_schema_json.copy()

# The full context passed to the agent loop each turn.
struct AgentContext(Movable):
    var system_prompt: String
    var tools: List[AgentTool]
    var model: String

    def __init__(out self, system_prompt: String, tools: List[AgentTool], model: String):
        self.system_prompt = system_prompt.copy()
        self.tools = tools.copy()
        self.model = model.copy()

# Message history entry — one of three roles.
# W2: flat union encoded as a tagged struct (Variants need extra work; keep simple).
struct HistoryEntry(Copyable, Movable):
    var role: String        # "user", "assistant", "tool_result"
    var content: String     # text content (or JSON for tool_result)
    var tool_call_id: String  # non-empty only for tool_result
    var tool_name: String     # non-empty only for tool_result

    def __init__(out self, role: String, content: String, tool_call_id: String = String(""), tool_name: String = String("")):
        self.role = role.copy()
        self.content = content.copy()
        self.tool_call_id = tool_call_id.copy()
        self.tool_name = tool_name.copy()

# Parsed tool call extracted from the model's text output.
struct ParsedToolCall(Copyable, Movable):
    var id: String
    var name: String
    var arguments_json: String

    def __init__(out self, id: String, name: String, arguments_json: String):
        self.id = id.copy()
        self.name = name.copy()
        self.arguments_json = arguments_json.copy()
