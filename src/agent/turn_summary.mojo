from std.python import Python, PythonObject


def summarize_turn_cap_default(max_turns: Int) raises -> String:
    """Produce a minimal turn-cap placeholder when no history is passed."""
    return (
        String("I hit the tool-iteration cap (")
        + String(max_turns)
        + String(" turns) before finishing the task.")
    )
