from std.collections import List
from std.python import Python, PythonObject
from agent.types import AgentContext, HistoryEntry, ParsedToolCall, AgentTool
from agent.tool_executor import dispatch_tool
from agent.steering import poll_steering, clear_steering
from agent.abort import clear_abort, is_aborted, request_abort

# Maximum tool call iterations per turn (prevents infinite loops).
comptime MAX_TOOL_ITERATIONS = 10
# Maximum retries on malformed tool call JSON.
comptime MAX_PARSE_RETRIES = 3

def extract_tool_calls(text: String) raises -> List[ParsedToolCall]:
    """Extract <tool_call>...</tool_call> blocks from text.

    Llama-3.1's tool calls appear as:
    <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>

    Returns list of ParsedToolCall. Empty list if no tool calls found.
    Parses JSON via Python's json module.
    """
    var py_json = Python.import_module("json")
    var builtins = Python.import_module("builtins")
    var results = List[ParsedToolCall]()

    # Use Python string methods for reliable find() with start offset.
    var py_text = builtins.str(text)
    var open_tag = "<tool_call>"
    var close_tag = "</tool_call>"
    var open_len = len(open_tag)
    var close_len = len(close_tag)

    var search_from = 0
    while True:
        var py_start = py_text.find(open_tag, search_from)
        var start = Int(py=py_start)
        if start == -1:
            break
        var inner_start = start + open_len
        var py_end = py_text.find(close_tag, inner_start)
        var end = Int(py=py_end)
        if end == -1:
            break
        # Extract the JSON string between the tags
        var py_json_str = py_text[inner_start:end]
        # Parse via Python json
        try:
            var parsed = py_json.loads(py_json_str)
            var name = String(parsed["name"])
            var py_empty = py_json.loads("{}")
            var args = String(py_json.dumps(parsed.get("arguments", py_empty)))
            # Generate a unique id (simple counter-based)
            var tc_id = String("tc_") + String(len(results))
            results.append(ParsedToolCall(tc_id, name, args))
        except:
            pass  # malformed JSON — skip this block
        search_from = end + close_len
    return results^

def format_history_as_chatml(
    system_prompt: String,
    history: List[HistoryEntry],
) raises -> String:
    """Format history as Llama-3 ChatML for MAX inference.

    Format:
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>\\n{system}\\n<|eot_id|>
    <|start_header_id|>user<|end_header_id|>\\n{content}\\n<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>\\n
    """
    var out = String("<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n")
    out += system_prompt
    out += String("\n<|eot_id|>\n")
    for i in range(len(history)):
        var entry = history[i].copy()
        if entry.role == "tool_result":
            # Encode tool results as user turn (Llama-3 convention)
            out += String("<|start_header_id|>user<|end_header_id|>\n")
            out += String("<tool_response>\n") + entry.content + String("\n</tool_response>")
            out += String("\n<|eot_id|>\n")
        else:
            out += String("<|start_header_id|>") + entry.role + String("<|end_header_id|>\n")
            out += entry.content
            out += String("\n<|eot_id|>\n")
    out += String("<|start_header_id|>assistant<|end_header_id|>\n")
    return out

def run_loop(
    user_input: String,
    context: AgentContext,
    model: String,
    max_new_tokens: Int = 512,
) raises -> String:
    """Run the ReAct loop for one user turn.

    1. Format history + new user message as ChatML
    2. Call MAX inference (via Python)
    3. Extract tool calls from response
    4. Execute each tool
    5. Append results to history, repeat from 2 (up to MAX_TOOL_ITERATIONS)
    6. Return final assistant text

    Returns the final assistant response text.
    """
    # W3: Clear abort flag and any stale steering messages from previous turn.
    clear_abort()
    clear_steering()

    var history = List[HistoryEntry]()
    history.append(HistoryEntry(String("user"), user_input))

    var iteration = 0
    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1

        # W3: Check abort before generating.
        if is_aborted():
            return String("[aborted]")

        # W3: Poll for steering messages (mid-turn user input).
        var steering_msg = poll_steering()
        if len(steering_msg) > 0:
            # Inject steering message as a user turn
            history.append(HistoryEntry(
                String("user"),
                String("[user] ") + steering_msg,
            ))

        # Format as ChatML
        var prompt = format_history_as_chatml(context.system_prompt, history)

        # W3: Simple context-size guard (approximate token count).
        # If the formatted prompt exceeds ~6000 chars (~1500 tokens),
        # trim the oldest middle turns to keep the model happy.
        # Full compaction (with summarization) happens in a separate pass.
        if len(prompt) > 24000:  # ~6000 tokens × 4 chars/token
            # Keep system prompt + first user + last 4 turns
            if len(history) > 6:
                var trimmed = List[HistoryEntry]()
                trimmed.append(history[0].copy())
                for j in range(len(history) - 4, len(history)):
                    trimmed.append(history[j].copy())
                history = trimmed^
                prompt = format_history_as_chatml(context.system_prompt, history)

        # Call MAX inference via Python
        var mod = Python.import_module("max_brain.pipeline")
        var response_text = String("")

        # Use generate_embedded (W1 embedded pipeline) when available;
        # fall back to run_one_shot (subprocess) if not.
        try:
            var result = mod.generate_embedded(prompt, model, max_new_tokens)
            response_text = String(result)
        except:
            # Fall back to subprocess if embedded pipeline not ready
            var rc = mod.run_one_shot(prompt, model, max_new_tokens)
            # run_one_shot writes to stdout directly; we can't capture it here
            # For now, return a placeholder (W2 will improve this)
            return String("[run_one_shot: output was written to stdout]")

        # Extract tool calls
        var tool_calls = extract_tool_calls(response_text)

        # No tool calls → final answer
        if len(tool_calls) == 0:
            return response_text

        # Append assistant message to history
        history.append(HistoryEntry(String("assistant"), response_text))

        # Execute each tool call and append results
        for i in range(len(tool_calls)):
            # W3: Check abort before each tool call.
            if is_aborted():
                return String("[aborted during tool execution]")
            var tc = tool_calls[i]
            var result = dispatch_tool(tc.name, tc.arguments_json)
            history.append(HistoryEntry(
                String("tool_result"),
                result,
                tc.id,
                tc.name,
            ))

    # Iteration cap hit
    return String("[agent: max tool iterations reached]")
