import logging

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label

logger = logging.getLogger("shovl.screens.confirm")


class ConfirmScreen(ModalScreen[bool]):
    """
    Modal screen to confirm an operation.
    """

    CSS_PATH = "../styles/confirm.tcss"

    initial_label: str

    ### Lifecycle methods ###

    def __init__(
        self,
        label: str,
    ) -> None:
        """
        Initialize the confirm screen.
        """
        super().__init__()

        self.initial_label = label

    def compose(self) -> ComposeResult:
        """
        Compose the confirm screen.
        """
        with Vertical(classes="confirm-container"):
            yield Label(self.initial_label, classes="prompt")
            yield Label("(y)es or (n)o", classes="confirm")

    ### Event handlers ###

    def on_key(self, event: Key) -> None:
        """
        Handle key presses within the input field. Closes the screen if the
        user hits the escape key.
        """
        if event.key == "escape":
            self.dismiss(False)
        elif event.key == "y":
            self.dismiss(True)
        elif event.key == "n":
            self.dismiss(False)
