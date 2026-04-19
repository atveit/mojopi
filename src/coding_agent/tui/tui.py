from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Collapsible
from textual.binding import Binding


class MojopiApp(App):
    BINDINGS = [Binding("ctrl+c", "interrupt", "Interrupt")]

    def compose(self) -> ComposeResult:
        yield RichLog(id="output", wrap=True)
        yield Input(id="prompt-input", placeholder="Enter message…")

    def action_interrupt(self) -> None:
        import agent.steering as steering
        import agent.abort as abort
        steering.push_steering("interrupt")
        abort.request_abort()

    def push_token(self, token: str) -> None:
        log = self.query_one("#output", RichLog)
        log.write(token, end="")

    def push_tool_call(self, name: str, result: str) -> None:
        log = self.query_one("#output", RichLog)
        collapsible = Collapsible(title=name)
        collapsible.compose_add_child(RichLog())
        log.write(f"[bold]{name}[/bold]\n{result}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        import agent.steering as steering
        steering.push_steering(event.value)
        event.input.clear()


def run_tui(
    model: str = "modularai/Llama-3.1-8B-Instruct-GGUF",
    session: str = "",
    tools: list = None,
) -> None:
    app = MojopiApp()
    app.run()


def create_app() -> MojopiApp:
    return MojopiApp()
