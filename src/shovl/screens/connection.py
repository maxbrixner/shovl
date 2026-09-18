import logging
import typing

from textual.app import ComposeResult
from textual.widgets import Footer, Header, Label, ListItem, ListView

from shovl import providers, schemas

from .base import BaseScreen

logger = logging.getLogger("shovl.screens.connection")


class ConnectionScreen(BaseScreen):
    """
    Screen for selecting a connection with filter functionality.
    """

    CSS_PATH = "../styles/connection.tcss"

    BINDINGS: typing.ClassVar[list[tuple[str, str, str]]] = [
        ("f", "filter", "filter"),
        ("q", "quit", "quit"),
    ]

    list_view: ListView

    all_connections: list[schemas.ServiceConfig]
    filtered_connections: list[schemas.ServiceConfig]

    provider: providers.ServiceProvider | None

    ### Lifecycle methods ###

    def __init__(self, config: schemas.ConfigSchema) -> None:
        """
        Initialize the connection screen.
        """
        super().__init__(config=config)

        self.all_connections = self.config.connections
        self.filtered_connections = self.all_connections.copy()

        self.provider = None

        self.set_title("shovl - Select Connection")

    def compose(self) -> ComposeResult:
        """
        Compose the connection selection screen.
        """
        yield Header()
        self.list_view = ListView(
            classes="connection-list", id="connection-list"
        )
        yield self.list_view
        yield Footer()

    ### Actions ###

    def action_quit(self) -> None:
        """
        Quit the app.
        """
        self.app.exit()  # type: ignore[reportUnknownMemberType]

    ### Event handlers ###

    def on_mount(self) -> None:
        """
        Initialize the screen when mounted. The connection list is refreshed
        and focused, and if there are any connections, the first one is
        selected.
        """
        self.refresh_view(show_truncated_hint=True)
        self.focus_view()

        if not self.filtered_connections:
            self.notify_info(
                "No connections found. Please add connections to your "
                "config file."
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """
        Handle Enter key on list items.
        """
        if not self.filtered_connections:
            return

        if (
            self.list_view.index is None
            or self.list_view.index < 0
            or self.list_view.index >= len(self.filtered_connections)
        ):
            return

        selected_connection = self.filtered_connections[self.list_view.index]
        self.run_in_thread(
            target=self.connect_worker,
            name="ConnectWorker",
            connection_config=selected_connection,
        )

    ### Class methods ###

    def filter_view(self) -> None:
        """
        Filter connections based on filter query. Meant to be called from a
        separate thread to avoid blocking the UI.
        """
        query = self.current_filter.lower().strip()

        if not query:
            self.filtered_connections = self.all_connections.copy()
        else:
            self.filtered_connections = [
                conn
                for conn in self.all_connections
                if (
                    query in conn.name.lower()
                    or query in conn.description.lower()
                )
            ]

    def refresh_view(self, show_truncated_hint: bool) -> None:
        """
        Refresh the connection list based on current filter.
        """
        self.list_view.clear()

        for index, connection in enumerate(self.filtered_connections):
            if (
                index >= self.config.gui.max_list_items
                and self.config.gui.max_list_items > 0
            ):
                break

            self.list_view.mount(
                ListItem(
                    Label(
                        connection.name,
                        classes="connection-name",
                    ),
                    Label(
                        connection.description,
                        classes="connection-description",
                    ),
                    classes="connection-item",
                ),
            )

        super().refresh_view(show_truncated_hint=show_truncated_hint)

    def focus_view(self) -> None:
        """
        Focus the connection list and select the first item.
        """
        self.list_view.focus()

        if self.filtered_connections:
            self.list_view.index = 0

    def connect_to_database(
        self,
        connection_config: schemas.DatabaseConfig,
    ) -> None:
        """
        Connect to a database using the provided connection configuration.
        We import the DatabaseProvider here since it depends on optional
        packages. Meant to be called from a separate thread to avoid blocking
        the UI.
        """
        if connection_config.url == "sqlite://":
            raise TypeError("SQLite in-memory connections are not supported.")

        self.test_database_provider()

        from shovl.providers.database import DatabaseProvider

        self.provider = DatabaseProvider(config=connection_config)

        self.provider.connect()

    def test_database_provider(self) -> None:
        """
        Test database provider to ensure they can be imported and used.
        Otherwise, exit gracefully with an error message suggesting how to
        install the required dependencies for database providers.
        """
        try:
            import sqlalchemy

            logger.info(f"SQLAlchemy version is {sqlalchemy.__version__}")
        except Exception as exception:
            logger.exception(
                "Failed to initialize database provider.", exc_info=exception
            )
            raise RuntimeError(
                "Failed to initialize database provider. Try installing "
                "SQLAlchemy."
            )

    def push_database_screen(
        self,
        connection_config: schemas.DatabaseConfig,
    ) -> None:
        """
        Push the database screen upon successful connection. We import the
        DatabaseScreen here since it depends on optional packages.
        """
        from shovl.providers.database import DatabaseProvider
        from shovl.screens.database import DatabaseScreen

        if not isinstance(self.provider, DatabaseProvider):
            raise TypeError("Invalid provider type")

        self.dismiss_status_screen()
        self.app.push_screen(  # type: ignore[reportUnknownMemberType]
            DatabaseScreen(
                config=self.config,
                connection=connection_config,
                provider=self.provider,
            )
        )

    def connect_to_bucket(
        self,
        connection_config: schemas.BucketConfig,
    ) -> None:
        """
        Connect to an S3 bucket using the provided connection configuration.
        We import the BucketProvider here since it depends on optional
        packages. Meant to be called from a separate thread to avoid blocking
        the UI.
        """
        self.test_bucket_provider()

        from shovl.providers.bucket import BucketProvider

        self.provider = BucketProvider(config=connection_config)

        self.provider.connect()

    def test_bucket_provider(self) -> None:
        """
        Test bucket provider to ensure they can be imported and used.
        Otherwise, exit gracefully with an error message suggesting how to
        install the required dependencies for bucket providers.
        """
        try:
            import boto3  # type: ignore[import-untyped]
            import botocore  # type: ignore[import-untyped]

            logger.info(
                f"Boto3 version is {boto3.__version__}, botocore version is "
                f"{botocore.__version__}"
            )
        except Exception as exception:
            logger.exception(
                "Failed to initialize bucket provider.", exc_info=exception
            )
            raise RuntimeError(
                "Failed to initialize bucket provider. Try installing boto3."
            )

    def push_bucket_screen(
        self,
        connection_config: schemas.BucketConfig,
    ) -> None:
        """
        Push the bucket screen upon successful connection. We import the
        BucketScreen here since it depends on optional packages.
        """
        from shovl.providers.bucket import BucketProvider
        from shovl.screens.bucket import BucketScreen

        if not isinstance(self.provider, BucketProvider):
            raise TypeError("Invalid provider type")

        self.dismiss_status_screen()
        self.app.push_screen(  # type: ignore[reportUnknownMemberType]
            BucketScreen(
                config=self.config,
                connection=connection_config,
                provider=self.provider,
            )
        )

    ### Workers ###

    def connect_worker(
        self,
        connection_config: schemas.ServiceConfig,
    ) -> None:
        """
        Worker method to connect to the selected service. This is run in a
        seperate thread to avoid blocking the UI.
        """
        try:
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                self.push_status_screen, label="Connecting..."
            )

            if isinstance(connection_config, schemas.DatabaseConfig):
                self.connect_to_database(connection_config=connection_config)
            else:
                self.connect_to_bucket(connection_config=connection_config)

            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]

            if isinstance(connection_config, schemas.DatabaseConfig):
                self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                    self.push_database_screen, connection_config
                )
            else:
                self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                    self.push_bucket_screen, connection_config
                )
        except Exception as exception:
            message = str(exception)
            logger.exception("Connection failed.", exc_info=exception)
            self.app.call_from_thread(self.dismiss_status_screen)  # type: ignore[reportUnknownMemberType]
            self.app.call_from_thread(self.focus_view)  # type: ignore[reportUnknownMemberType]
            self.app.call_from_thread(  # type: ignore[reportUnknownMemberType]
                lambda: self.notify_error(f"Unable to connect: {message}")
            )
