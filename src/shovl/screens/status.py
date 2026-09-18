import logging
from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, LoadingIndicator

logger = logging.getLogger("shovl.screens.status")


class StatusScreen(ModalScreen[None]):
    """
    Screen to display a status.
    """

    CSS_PATH = "../styles/status.tcss"

    label: Label

    initial_label: str | None

    abort_callback: Callable[[], None] | None

    ### Lifecycle methods ###

    def __init__(
        self,
        label: str | None = None,
        abort_callback: Callable[[], None] | None = None,
    ) -> None:
        """
        Initialize the status screen.
        """
        super().__init__()

        self.initial_label = label

        self.abort_callback = abort_callback

    def compose(self) -> ComposeResult:
        """
        Compose the status screen.
        """
        with Vertical(classes="status-container"):
            label = self.initial_label if self.initial_label else "Loading..."
            self.label = Label(label, classes="label")
            yield self.label

            with Vertical():
                yield LoadingIndicator(classes="indicator")

            if self.abort_callback is not None:
                yield Label("(a)bort", classes="abort")

    ### Event handlers ###

    def on_key(self, event: Key) -> None:
        """
        Handle key presses within the input field. Closes the screen if the
        user hits the escape key.
        """
        if event.key == "a" and self.abort_callback is not None:
            self.abort_callback()

    ### Class methods ###

    def update_label(self, label: str) -> None:
        """
        Update label.
        """
        self.label.update(content=label)
