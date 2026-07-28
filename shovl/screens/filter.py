import logging
from typing import Callable, Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Input

logger = logging.getLogger("shovl.screens.filter")


class FilterScreen(ModalScreen):
    """
    Screen to filter a list of items.
    """

    BINDINGS = [("escape", "cancel", "cancel")]

    CSS_PATH = "../styles/filter.tcss"

    input: Input

    change_callback: Callable[[str], None]
    confirm_callback: Callable[[str], None]
    cancel_callback: Callable[[str], None]

    current_filter: str

    debounce_timer: Optional[Timer]

    ### Lifecycle methods ###

    def __init__(
        self,
        current_filter: str = "",
        change_callback: Callable[[str], None] = lambda x: None,
        confirm_callback: Callable[[str], None] = lambda x: None,
        cancel_callback: Callable[[str], None] = lambda x: None,
    ) -> None:
        """
        Initialize the filter screen.
        """
        super().__init__()

        self.change_callback = change_callback
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self.current_filter = current_filter
        self.debounce_timer = None

    def compose(self) -> ComposeResult:
        """
        Compose the filter screen.
        """
        self.input = Input(
            classes="input",
            placeholder="Type to filter...",
            value=self.current_filter,
        )
        yield self.input

    ### Actions ###

    def action_cancel(self) -> None:
        """
        Cancel the filter operation.
        """
        if self.debounce_timer:
            self.debounce_timer.stop()
            self.debounce_timer = None

        self.cancel_callback(self.input.value)

    ### Event handlers ###

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Handle filter input changes with debouncing.
        """
        if self.debounce_timer:
            self.debounce_timer.stop()

        self.debounce_timer = self.set_timer(
            0.5,
            lambda: self.change_callback(event.value),
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle filter input submission.
        """
        if self.debounce_timer:
            self.debounce_timer.stop()
            self.debounce_timer = None

        self.confirm_callback(event.value)
