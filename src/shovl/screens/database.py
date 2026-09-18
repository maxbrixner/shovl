import copy
import logging
import pathlib
import typing

from rich.text import Text
from textual.widgets import DataTable

from shovl import providers, schemas
from shovl.providers.database import DatabaseProvider

from .path import PathScreen
from .service import ServiceScreen

logger = logging.getLogger("shovl.screens.database")


class DatabaseScreen(ServiceScreen):
    """
    Screen to browse the contents of a database.
    """

    BINDINGS: typing.ClassVar[list[tuple[str, str, str]]] = [
        ("backspace", "back", "back"),
        ("f", "filter", "filter"),
        ("p", "preview", "preview"),
        ("y", "query", "query"),
    ]

    last_query_file: pathlib.Path | None

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
        super().__init__(
            config=config, connection=connection, provider=provider
        )
        self.last_query_file = None

    ### Actions ###

    def action_preview(self) -> None:
        """
        Preview the selected database entity.
        """
        entity = self.get_selected_row()

        assert isinstance(entity, schemas.DatabaseEntity)

        if entity and entity.type in (
            schemas.DatabaseEntityType.table,
            schemas.DatabaseEntityType.view,
        ):
            self.run_in_thread(
                target=self.preview_worker,
                name="PreviewWorker",
                entity=entity,
            )

            self.current_filter = ""
        else:
            self.notify_info("Please select a table or view to preview.")

    def action_query(self) -> None:
        """
        Start a database query using an SQL file.
        """

        def callback(path: pathlib.Path | None) -> None:
            self.last_query_file = path
            if path:
                self.run_in_thread(
                    target=self.query_worker,
                    name="QueryWorker",
                    filepath=path,
                )

        self.app.push_screen(  # type: ignore[reportUnknownMemberType]
            PathScreen(
                label="Enter the path to an SQL file:",
                path=self.last_query_file,
                restrictions=[schemas.PathRestriction.must_be_file],
            ),
            callback=callback,
        )

    ### Event handlers ###

    def on_mount(self) -> None:
        """
        Handle the screen mount event by initializing the table, i.e. liting
        availables schemas.
        """
        self.run_in_thread(
            target=self.inspection_worker,
            name="InspectionWorker",
            entity=schemas.DatabaseEntity(
                name="Schemas",
                type=schemas.DatabaseEntityType.schemas,
            ),
            add_current_to_history=False,
        )

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        """
        Handle Enter key on list items.
        """
        entity = self.get_selected_row()

        assert isinstance(entity, schemas.DatabaseEntity)

        if entity and entity.type in (
            schemas.DatabaseEntityType.schema,
            schemas.DatabaseEntityType.tables,
            schemas.DatabaseEntityType.views,
            schemas.DatabaseEntityType.table,
            schemas.DatabaseEntityType.view,
        ):
            self.run_in_thread(
                target=self.inspection_worker,
                name="InspectionWorker",
                entity=entity,
                add_current_to_history=True,
            )

    ### Class methods ###

    def inspect(
        self, entity: schemas.ServiceEntity, add_current_to_history: bool
    ) -> None:
        """
        Inspect a specific row in the table. This method is meant to be
        called from a separate thread to avoid blocking the UI.
        """
        assert isinstance(entity, schemas.DatabaseEntity)
        assert isinstance(self.provider, DatabaseProvider)

        match entity.type:
            case schemas.DatabaseEntityType.schemas:
                entities = self.provider.inspect_schemas()
            case schemas.DatabaseEntityType.schema:
                entities = [
                    schemas.DatabaseEntity(
                        name="tables",
                        type=schemas.DatabaseEntityType.tables,
                        dbschema=entity.name,
                    ),
                    schemas.DatabaseEntity(
                        name="views",
                        type=schemas.DatabaseEntityType.views,
                        dbschema=entity.name,
                    ),
                ]
            case schemas.DatabaseEntityType.tables:
                assert entity.dbschema
                entities = self.provider.inspect_tables(schema=entity.dbschema)
            case schemas.DatabaseEntityType.views:
                assert entity.dbschema
                entities = self.provider.inspect_views(schema=entity.dbschema)
            case schemas.DatabaseEntityType.table:
                assert entity.dbschema
                entities = self.provider.inspect_table(
                    table_name=entity.name, schema=entity.dbschema
                )
            case schemas.DatabaseEntityType.view:
                assert entity.dbschema
                entities = self.provider.inspect_view(
                    view_name=entity.name, schema=entity.dbschema
                )
            case _:
                raise TypeError(f"Unsupported entity type: {entity.type}")

        self.all_entities = entities
        self.filtered_entities = copy.copy(list(self.all_entities))

        if self.current_entity and add_current_to_history:
            self.add_to_history()

        self.current_filter = ""

        self.current_entity = entity

    def fetch_preview(self, entity: schemas.DatabaseEntity) -> None:
        """
        Preview a table or view. Meant to be called from a separate
        thread to avoid blocking the UI.
        """
        assert isinstance(self.provider, DatabaseProvider)
        assert entity.dbschema

        self.all_entities = self.provider.fetch_preview(
            schema=entity.dbschema,
            name=entity.name,
        )
        self.filtered_entities = copy.copy(list(self.all_entities))

        if self.current_entity:
            self.add_to_history()

        self.current_filter = ""

        self.current_entity = entity

    def execute_query(self, filepath: pathlib.Path) -> int:
        """
        Execute a query and preview the result. Meant to be called from a
        separate thread to avoid blocking the UI.
        """
        assert isinstance(self.provider, DatabaseProvider)

        if not filepath.exists() or not filepath.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        with filepath.open("r") as file:
            query = file.read()

        entities, affected_rows = self.provider.execute_query(query=query)

        if entities:  # i.e. a select statement
            self.all_entities, _ = self.provider.execute_query(query=query)
            self.filtered_entities = copy.copy(list(self.all_entities))

            if self.current_entity:
                self.add_to_history()

            self.current_filter = ""

            self.current_entity = None

            return 0
        else:  # i.e. a create/update/insert/... statement
            return affected_rows

    def filter_view(self) -> None:
        """
        Filter database entities based on filter query. Meant to
        be called from a separate thread to avoid blocking the UI.
        """
        query = self.current_filter.lower().strip()

        if not query:
            self.filtered_entities = copy.copy(list(self.all_entities))
        else:
            self.filtered_entities: typing.Sequence[schemas.ServiceEntity] = []
            for entity in self.all_entities:
                assert isinstance(entity, schemas.DatabaseEntity)
                if not entity.data and query in entity.name.lower():
                    self.filtered_entities.append(entity)
                    continue
                if not entity.data:
                    continue
                if any(
                    query in str(value).lower()
                    for value in entity.data.values()
                ):
                    self.filtered_entities.append(entity)

    def add_columns(self, entity: schemas.ServiceEntity) -> None:
        """
        Add columns to the table based on the type of entity.
        """
        assert isinstance(entity, schemas.DatabaseEntity)

        match entity.type:
            case (
                schemas.DatabaseEntityType.schemas
                | schemas.DatabaseEntityType.schema
                | schemas.DatabaseEntityType.tables
                | schemas.DatabaseEntityType.views
                | schemas.DatabaseEntityType.table
                | schemas.DatabaseEntityType.view
            ):
                self.table.add_columns("Name", "Type")  # type: ignore[reportUnknownMemberType]
            case schemas.DatabaseEntityType.column:
                self.table.add_columns("Name", "Data Type", "Nullable", "Type")  # type: ignore[reportUnknownMemberType]
            case schemas.DatabaseEntityType.row:
                assert entity.data is not None
                self.table.add_columns(*entity.data.keys())  # type: ignore[reportUnknownMemberType]

    def add_row(self, entity: schemas.ServiceEntity) -> None:
        """
        Add a row to the table.
        """
        assert isinstance(entity, schemas.DatabaseEntity)

        name = self.get_entity_display_name(entity=entity)

        primary_color = self.app.theme_variables.get("primary")  # type: ignore[reportUnknownMemberType]

        if entity.type in (
            schemas.DatabaseEntityType.schemas,
            schemas.DatabaseEntityType.schema,
            schemas.DatabaseEntityType.tables,
            schemas.DatabaseEntityType.views,
            schemas.DatabaseEntityType.table,
            schemas.DatabaseEntityType.view,
        ):
            self.table.add_row(  # type: ignore[reportUnknownMemberType]
                Text(name, style=f"bold {primary_color}"), entity.type.value
            )
        elif entity.type == schemas.DatabaseEntityType.column:
            self.table.add_row(  # type: ignore[reportUnknownMemberType]
                name,
                entity.datatype or "",
                "True" if entity.nullable else "False",
                entity.type.value,
            )
        elif entity.type == schemas.DatabaseEntityType.row:
            assert entity.data is not None
            self.table.add_row(*[str(value) for value in entity.data.values()])  # type: ignore[reportUnknownMemberType]

    def get_entity_display_name(self, entity: schemas.DatabaseEntity) -> str:
        """
        Get the display name for a database entity.
        """
        return entity.name

    ### Workers ###

    def preview_worker(
        self,
        entity: schemas.DatabaseEntity,
    ) -> None:
        """
        Preview a database table.
        """
        try:
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                self.push_status_screen, label="Fetching preview..."
            )

            self.fetch_preview(entity=entity)

            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                self.refresh_view, show_truncated_hint=True
            )

            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]
        except Exception as exception:
            logger.exception("Preview failed.", exc_info=exception)
            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]
            self.app.call_from_thread(self.focus_view)  # type: ignore[reportUnknownMemberType]
            message = str(exception)
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                lambda: self.notify_error(f"Preview failed: {message}")
            )

    def query_worker(
        self,
        filepath: pathlib.Path,
    ) -> None:
        """
        Execute a database query.
        """
        try:
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                self.push_status_screen, label="Executing query..."
            )

            affected_rows = self.execute_query(filepath=filepath)

            if affected_rows >= 0:
                self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                    lambda: self.notify_info(
                        f"Query executed successfully. Affected rows: "
                        f"{affected_rows}"
                    )
                )
            else:
                self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                    lambda: self.notify_info(
                        "Query executed successfully. No affected rows."
                    )
                )

            # todo: refresh?

            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                self.refresh_view, show_truncated_hint=True
            )

            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]
        except Exception as exception:
            logger.exception("Query failed.", exc_info=exception)
            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]
            self.app.call_from_thread(self.focus_view)  # type: ignore[reportUnknownMemberType]
            message = str(exception)
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                lambda: self.notify_error(f"Query failed: {message}")
            )
