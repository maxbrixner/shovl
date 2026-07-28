import logging
import pathlib
import threading
from typing import Any, Callable, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Input, Label

import shovl.schemas as schemas

logger = logging.getLogger("shovl.screens.path")


class PathScreen(ModalScreen[pathlib.Path | None]):
    """
    Screen to enter a local file path.
    """

    CSS_PATH = "../styles/path.tcss"

    label: Label
    hint: Label

    worker: threading.Thread | None
    path_changed_event: threading.Event

    initial_label: str | None
    initial_path: pathlib.Path | None

    current_path: str
    restrictions: List[schemas.PathRestriction]

    ### Lifecycle methods ###

    def __init__(
        self,
        label: Optional[str] = None,
        path: Optional[pathlib.Path] = None,
        restrictions: List[schemas.PathRestriction] = [],
    ) -> None:
        """
        Initialize the path screen.
        """
        super().__init__()

        self.initial_label = label
        self.initial_path = path

        self.worker = None
        self.path_changed_event = threading.Event()

        self.current_path = str(path) if path else ""
        self.restrictions = restrictions

    def compose(self) -> ComposeResult:
        """
        Compose the path screen.
        """
        with Vertical(classes="path-container"):
            label = (
                self.initial_label if self.initial_label else "Enter local path"
            )
            path = (
                self.initial_path if self.initial_path else pathlib.Path.cwd()
            )
            self.current_path = str(path)
            self.label = Label(label, classes="label")
            yield self.label
            yield Input(classes="input", value=self.current_path)
            self.hint = Label("Checking path...", classes="hint")
            yield self.hint

    ### Event handlers ###

    def on_mount(self) -> None:
        """
        Start the path check worker when the screen is mounted.
        """
        self.run_in_thread(
            self.path_check_worker,
            name="PathCheckWorker",
            callback=self.path_checked_callback,
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Handle changes to the input field.
        """
        self.current_path = event.value
        self.path_changed_event.set()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle submission of the input field. Closes the screen if the path is
        valid.
        """
        if self.check_path(self.current_path):
            self.dismiss(pathlib.Path(self.current_path))

    def on_key(self, event: Key) -> None:
        """
        Handle key presses within the input field. Closes the screen if the
        user hits the escape key.
        """
        if event.key == "escape":
            self.dismiss(None)

    ### Callbacks ###

    def path_checked_callback(self, valid: bool) -> None:
        """
        Updates the label indicating whether the path is valid or not.
        """
        if valid:
            self.hint.update(content="✅ Path is valid")
        else:
            self.hint.update(content="🛑 Path is not valid")

    ### Class methods ###

    def run_in_thread(
        self,
        target: Callable,
        name: str,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """
        Run the given target function in a separate thread. Shows the status
        screen while the thread is running.
        """
        if self.worker and self.worker.is_alive():
            raise Exception("Worker is already running")

        self.worker = threading.Thread(
            target=target, daemon=True, name=name, args=args, kwargs=kwargs
        )
        self.worker.start()

    def check_path(self, path: pathlib.Path | str) -> bool:
        """
        Return True is a path is an existing directory or False otherwise.
        """
        if isinstance(path, str):
            path = pathlib.Path(path)

        if (
            schemas.PathRestriction.must_exist in self.restrictions
            and not path.exists()
        ):
            return False

        if (
            schemas.PathRestriction.must_be_directory in self.restrictions
            and not path.is_dir()
        ):
            return False

        if (
            schemas.PathRestriction.must_be_file in self.restrictions
            and not path.is_file()
        ):
            return False

        return True

    ### Worker methods ###

    def path_check_worker(
        self,
        callback: Callable[[bool], None] = lambda x: None,
    ) -> None:
        """
        Check if the path is valid.
        """
        while True:
            self.path_changed_event.wait()

            self.app.call_from_thread(
                callback, self.check_path(path=self.current_path)
            )

            self.path_changed_event.clear()
