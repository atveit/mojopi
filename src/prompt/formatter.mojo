# Llama-3-Instruct single-turn ChatML formatting.
# For C3 we only need single-turn user -> assistant. Multi-turn + system prompt
# arrive in W2 when the full ReAct loop is ported.

def format_llama3_single_turn(user_message: String) -> String:
    """Return the prompt string to feed MAX's TextGenerationPipeline."""
    return (
        "<|begin_of_text|>"
        + "<|start_header_id|>user<|end_header_id|>\n\n"
        + user_message
        + "<|eot_id|>"
        + "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
