import logging
from collections.abc import Sequence

from textual.app import ComposeResult
from textual.widgets import DataTable, Footer, Header

from shovl import providers, schemas

from .base import BaseScreen

logger = logging.getLogger("shovl.screens.service")


class ServiceScreen(BaseScreen):
    """
    Base service screen. Inherited by all service screens (e.g. database,
    bucket, etc.) to provide common functionality such as displaying
    connection info, handling common keybindings, etc.
    """

    CSS_PATH = "../styles/service.tcss"

    table: DataTable

    connection: schemas.ServiceConfig
    provider: providers.ServiceProvider

    history: list[schemas.HistoryItem]
    all_entities: Sequence[schemas.ServiceEntity]
    filtered_entites: Sequence[schemas.ServiceEntity]

    current_entity: schemas.ServiceEntity | None

    ### Lifecycle methods ###

    def __init__(
        self,
        config: schemas.ConfigSchema,
        connection: schemas.ServiceConfig,
        provider: providers.ServiceProvider,
    ) -> None:
        """
        Initialize the database screen.
        """
        super().__init__(config=config)
        self.connection = connection
        self.provider = provider

        self.history = []
        self.all_entities = []
        self.filtered_entities = []

        self.current_entity = None

        self.set_title(f"shovl - {self.connection.name}")

    def compose(self) -> ComposeResult:
        """
        Compose the service screen.
        """
        yield Header()
        self.table = DataTable(
            classes="table",
            id="table",
        )
        yield self.table
        yield Footer()

    ### Actions ###

    def action_back(self) -> None:
        """
        Go back one step in history, if available.
        """
        history_item = self.go_back_in_history()

        if history_item:
            self.run_in_thread(
                target=self.inspection_worker,
                name="InspectionWorker",
                entity=history_item.entity,
                add_current_to_history=False,
                apply_filter=history_item.filter,
                select_row=history_item.selected_row,
            )
        else:
            self.provider.disconnect()
            self.app.pop_screen()

    ### Class methods ###

    def focus_view(self) -> None:
        """
        Focus the tabe.
        """
        self.table.focus()

    def add_columns(self, entity: schemas.ServiceEntity) -> None:
        """
        Add columns to the table based on the type of entity.
        """
        raise NotImplementedError(
            "add_columns must be implemented by subclasses"
        )

    def add_row(self, entity: schemas.ServiceEntity) -> None:
        """
        Add a row to the table.
        """
        raise NotImplementedError("add_rows must be implemented by subclasses")

    def refresh_view(self, show_truncated_hint: bool) -> None:
        """
        Add rows to the table based on a list of entities.
        """
        with self.app.batch_update():
            self.table.clear(columns=True)

            if not self.filtered_entities:
                super().refresh_view(show_truncated_hint=show_truncated_hint)
                return

            self.add_columns(entity=self.filtered_entities[0])

            for index, entity in enumerate(self.filtered_entities):
                if (
                    index >= self.config.gui.max_list_items
                    and self.config.gui.max_list_items > 0
                ):
                    if show_truncated_hint:
                        self.notify_info(
                            f"Showing first {self.config.gui.max_list_items} "
                            f"items. Refine your filter to see more."
                        )
                    break

                self.add_row(entity=entity)

        super().refresh_view(show_truncated_hint=show_truncated_hint)

    def get_selected_row(self) -> schemas.ServiceEntity | None:
        """
        Get the data of the currently selected row in the table and return it
        as a BucketEntity object.
        """
        if self.table.cursor_row is None:
            return None

        if self.table.cursor_row >= len(self.filtered_entities):
            return None

        return self.filtered_entities[self.table.cursor_row]

    def add_to_history(self) -> None:
        """
        Add the current state to the history stack.
        """
        if self.current_entity is None:
            return

        self.history.append(
            schemas.HistoryItem(
                entity=self.current_entity,
                filter=self.current_filter,
                selected_row=self.table.cursor_row,
            )
        )

    def go_back_in_history(self) -> schemas.HistoryItem | None:
        """
        Go back in history and return the previous entity, or None if at root.
        """
        if len(self.history) >= 1:
            return self.history.pop()
        elif len(self.history) == 0:
            return None

    def inspect(
        self, entity: schemas.ServiceEntity, add_current_to_history: bool
    ) -> None:
        """
        Inspect a bucket entity and update the view with the results. This
        method is meant to be called from a separate thread to avoid blocking
        the UI.
        """
        raise NotImplementedError("inspect must be implemented by subclasses")

    def filter_view(self) -> None:
        """
        Filter entities based on filter query. Meant to be called from a
        separate thread to avoid blocking the UI.
        """
        raise NotImplementedError(
            "filter_view must be implemented by subclasses"
        )

    ### Workers ###

    def inspection_worker(
        self,
        entity: schemas.BucketEntity,
        add_current_to_history: bool,
        apply_filter: str | None = None,
        select_row: int | None = None,
    ) -> None:
        """
        Inspect a service entity.
        """
        try:
            self.app.call_from_thread(
                self.push_status_screen, label="Inspecting..."
            )

            self.inspect(
                entity=entity, add_current_to_history=add_current_to_history
            )

            if apply_filter:
                self.current_filter = apply_filter
                self.filter_view()

            self.app.call_from_thread(
                self.refresh_view, show_truncated_hint=True
            )

            if select_row and select_row < len(self.filtered_entities):
                self.app.call_from_thread(
                    lambda: self.table.move_cursor(
                        row=select_row, column=0, animate=False
                    )
                )

            self.app.call_from_thread(self.dismiss_status_screen)
        except Exception as exception:
            logger.exception(f"Inspection failed: {exception}")
            self.app.call_from_thread(self.dismiss_status_screen)
            self.app.call_from_thread(self.focus_view)
            message = str(exception)
            self.app.call_from_thread(
                lambda: self.notify_error(
                    f"Unable to inspect entity: {message}"
                )
            )
