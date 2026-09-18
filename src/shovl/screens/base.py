import logging
import threading
from collections.abc import Callable
from typing import Any

from textual.screen import Screen

from shovl import schemas, services

from .filter import FilterScreen
from .status import StatusScreen

logger = logging.getLogger("shovl.screens.base")


class BaseScreen(Screen):
    """
    Base screen. Inherited by all other screens. Offers common functionality
    like status and filter handling.
    """

    config: schemas.ConfigSchema

    status_screen: StatusScreen | None
    filter_screen: FilterScreen | None

    worker: threading.Thread | None

    current_filter: str
    filter_changed_signal: threading.Event
    filter_closed_signal: threading.Event

    refreshed_signal: threading.Event

    ### Lifecycle methods ###

    def __init__(self, config: schemas.ConfigSchema) -> None:
        """
        Initialize the service screen.
        """
        super().__init__()

        self.config = config

        self.status_screen = None
        self.filter_screen = None

        self.worker = None

        self.current_filter = ""
        self.filter_changed_signal = threading.Event()
        self.filter_closed_signal = threading.Event()

        self.refreshed_signal = threading.Event()

    ### Actions ###

    def action_filter(self) -> None:
        """
        Start the filter worker showing the filter screen.
        """
        self.run_in_thread(self.filter_worker, name="FilterWorker")

    ### Callbacks ###

    def filter_change_callback(self, query: str) -> None:
        """
        Callback for the filter modal. Called anytime the input value changes.
        """
        self.current_filter = query
        self.filter_changed_signal.set()

    def filter_closed_callback(self, query: str) -> None:
        """
        Callback for the filter modal. Called when the user hits the enter key
        within the filter modal.
        """
        self.current_filter = query
        self.filter_closed_signal.set()
        self.filter_changed_signal.set()

    ### Class methods ###

    def set_title(self, title: str) -> None:
        """
        Set the title of the screen.
        """
        self.title = services.shorten_string(title, 30)

    def notify_error(self, message: str) -> None:
        """
        Notify the user of an error.
        """
        logger.debug(f"Notifying user of an error: {message}")
        self.app.notify(
            services.shorten_string(message, 200),
            title="Error",
            severity="error",
        )

    def notify_info(self, message: str) -> None:
        """
        Notify the user of an informational message.
        """
        logger.debug(f"Notifying user of an informational message: {message}")
        self.app.notify(
            services.shorten_string(message, 200),
            title="Info",
            severity="information",
        )

    def run_in_thread(
        self,
        target: Callable,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Run the given target function in a separate thread. Shows the status
        screen while the thread is running.
        """
        if self.worker and self.worker.is_alive():
            raise Exception("Worker is already running.")

        self.worker = threading.Thread(
            target=target, daemon=True, name=name, args=args, kwargs=kwargs
        )
        self.worker.start()

    def push_status_screen(
        self,
        label: str | None = None,
        abort_callback: Callable | None = None,
    ) -> None:
        """
        Push the status screen.
        """
        if self.status_screen:
            raise Exception("Status screen is already being shown.")

        self.status_screen = StatusScreen(
            label=label, abort_callback=abort_callback
        )
        self.app.push_screen(self.status_screen)

    def dismiss_status_screen(self) -> None:
        """
        Dismiss the status screen.
        """
        if self.status_screen:
            self.status_screen.dismiss()
            self.status_screen = None

    def push_filter_screen(self) -> None:
        """
        Show the modal filter screen.
        """
        if self.filter_screen:
            raise Exception("Filter screen is already being shown.")

        self.filter_changed_signal.clear()
        self.filter_closed_signal.clear()
        self.refreshed_signal.clear()

        self.filter_screen = FilterScreen(
            current_filter=self.current_filter,
            change_callback=self.filter_change_callback,
            confirm_callback=self.filter_closed_callback,
            cancel_callback=self.filter_closed_callback,
        )
        self.app.push_screen(self.filter_screen)

    def dismiss_filter_screen(self) -> None:
        """
        Dismiss the modal filter screen.
        """
        if self.filter_screen:
            self.filter_screen.dismiss()
            self.filter_screen = None

    def filter_view(self) -> None:
        """
        Handle the filter operation for the default filter worker. Has to be
        implemented by the subclass.
        """
        raise NotImplementedError(
            "Filter method must be implemented by subclass."
        )

    def refresh_view(self, show_truncated_hint: bool) -> None:
        """
        Handle the refresh operation for the default filter worker. Has to be
        implemented by the subclass. Must call super method!
        """
        self.call_after_refresh(self.refreshed_signal.set)

    def focus_view(self) -> None:
        """
        Focus the main view after the default filter worker has been dismissed.
        Has to be implemented by the subclass.
        """
        raise NotImplementedError(
            "Focus main method must be implemented by subclass."
        )

    ### Workers ###

    def filter_worker(self) -> None:
        """
        Default implementation for a filter worker. Shows the filter screen and
        waits for the filter signal to be set. When the signal is set, it
        checks the filter status and either cancels, confirms, or updates the
        filter results. This loop continues until the filter is either confirmed
        or cancelled.
        """
        try:
            self.app.call_from_thread(self.push_filter_screen)

            while True:
                self.filter_changed_signal.wait()

                self.filter_view()
                self.app.call_from_thread(
                    self.refresh_view, show_truncated_hint=False
                )

                # We wait after the refresh is done before we potentially
                # update the filter again, because the refresh might take some
                # time and we don't want to update the filter results while the
                # refresh is still running to avoid potential race conditions.
                self.refreshed_signal.wait()
                self.refreshed_signal.clear()

                if self.filter_closed_signal.is_set():
                    break

                self.filter_changed_signal.clear()
        except Exception as exception:
            logger.exception(f"Error in filter worker: {exception}")
            message = str(exception)
            self.app.call_from_thread(
                lambda: self.notify_error(
                    f"Unable to filter connections: {message}"
                )
            )

        self.app.call_from_thread(self.dismiss_filter_screen)
        self.app.call_from_thread(self.focus_view)
