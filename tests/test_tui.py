import sys
sys.path.insert(0, "src")


def test_tui_module_importable():
    from coding_agent.tui import tui
    assert hasattr(tui, "MojopiApp")
    assert hasattr(tui, "run_tui")
    assert hasattr(tui, "create_app")


def test_mojopi_app_instantiable():
    from coding_agent.tui.tui import create_app
    app = create_app()
    assert app is not None


def test_push_token_method_exists():
    from coding_agent.tui.tui import create_app
    app = create_app()
    assert hasattr(app, "push_token")
    assert callable(app.push_token)


def test_push_tool_call_method_exists():
    from coding_agent.tui.tui import create_app
    app = create_app()
    assert hasattr(app, "push_tool_call")
    assert callable(app.push_tool_call)


def test_run_tui_is_callable():
    from coding_agent.tui import tui
    assert callable(tui.run_tui)


def test_tui_wires_steering_on_interrupt():
    """action_interrupt pushes to steering queue."""
    import sys
    sys.path.insert(0, "src")
    import agent.steering as steering
    import agent.abort as abort
    from coding_agent.tui.tui import create_app

    pushed = []
    original_push = steering.push_steering
    original_abort = abort.request_abort
    steering.push_steering = lambda msg: pushed.append(msg)
    abort.request_abort = lambda: None
    try:
        app = create_app()
        app.action_interrupt()
        assert len(pushed) == 1
        assert pushed[0] == "interrupt"
    finally:
        steering.push_steering = original_push
        abort.request_abort = original_abort
