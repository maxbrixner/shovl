import logging
from typing import Sequence, Tuple

import sqlalchemy

import shovl.schemas as schemas
import shovl.services as services

from .service import ServiceProvider

logger = logging.getLogger("shovl.providers.database")


class DatabaseProvider(ServiceProvider):
    """
    Database provider for connecting to and inspecting databases using
    SQLAlchemy.
    """

    engine: sqlalchemy.engine.Engine | None
    inspector: sqlalchemy.Inspector | None
    connection: sqlalchemy.Connection | None

    def _cleanup(self) -> None:
        """
        Cleanup the provider's state.
        """
        self.engine = None
        self.inspector = None
        self.connection = None

    @property
    def connected(self) -> bool:
        """
        Check if the provider is connected to a database.
        """
        return (
            self.engine is not None
            or self.inspector is not None
            or self.connection is not None
        )

    def connect(self) -> None:
        """
        Connect to a database.
        """
        logger.info(f"Connecting to database: {self.config.name}")

        assert isinstance(self.config, schemas.DatabaseConfig)

        if self.connected:
            self.disconnect()

        self.engine = sqlalchemy.create_engine(
            url=services.resolve_credentials(self.config.url, parse_url=True),
            **(self.config.engine_parameters or {}),
        )

        self.inspector = sqlalchemy.inspect(self.engine)

        self.connection = self.engine.connect()

        logger.info(f"Successfully connected to database: {self.config.name}")

    def disconnect(self) -> None:
        """
        Disconnect from the database.
        """
        logger.info(f"Disconnecting from database: {self.config.name}")

        if self.connection:
            self.connection.close()

        if self.engine:
            self.engine.dispose()

        self._cleanup()

        logger.info(
            f"Successfully disconnected from database: {self.config.name}"
        )

    def inspect_schemas(self) -> Sequence[schemas.DatabaseEntity]:
        """
        Inspect the database's schemas.
        """
        logger.debug(f"Inspecting schemas in database: {self.config.name}")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.inspector is not None

        names = self.inspector.get_schema_names()

        result = [
            schemas.DatabaseEntity(
                name=name,
                type=schemas.DatabaseEntityType.schema,
            )
            for name in names
        ]

        result = sorted(result, key=lambda x: x.name)

        logger.debug(
            f"Successfully inspected schemas in database: {self.config.name}"
        )

        return result

    def inspect_tables(self, schema: str) -> Sequence[schemas.DatabaseEntity]:
        """
        Inspect a schema's tables.
        """
        logger.debug(f"Inspecting tables in schema '{schema}'.")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.inspector is not None

        names = self.inspector.get_table_names(schema=schema)

        result = [
            schemas.DatabaseEntity(
                name=name,
                type=schemas.DatabaseEntityType.table,
                dbschema=schema,
            )
            for name in names
        ]

        result = sorted(result, key=lambda x: x.name)

        logger.debug(f"Successfully inspected tables in schema '{schema}'.")

        return result

    def inspect_views(self, schema: str) -> Sequence[schemas.DatabaseEntity]:
        """
        Inspect a schema's views.
        """
        logger.debug(f"Inspecting views in schema '{schema}'.")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.inspector is not None

        names = self.inspector.get_view_names(schema=schema)

        result = [
            schemas.DatabaseEntity(
                name=name,
                type=schemas.DatabaseEntityType.view,
                dbschema=schema,
            )
            for name in names
        ]

        result = sorted(result, key=lambda x: x.name)

        logger.debug(f"Successfully inspected views in schema '{schema}'.")

        return result

    def inspect_table(
        self, schema: str, table_name: str
    ) -> Sequence[schemas.DatabaseEntity]:
        """
        Inspect a table, i.e. return its columns.
        """
        logger.debug(f"Inspecting table '{table_name}' in schema '{schema}'.")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.inspector is not None

        columns = self.inspector.get_columns(
            table_name=table_name, schema=schema
        )

        result = []
        for column in columns:
            result.append(
                schemas.DatabaseEntity(
                    name=column["name"],
                    type=schemas.DatabaseEntityType.column,
                    dbschema=schema,
                    datatype=str(column["type"] or ""),
                    nullable=column["nullable"] or True,
                )
            )

        result = sorted(result, key=lambda x: x.name)

        logger.debug(
            f"Successfully inspected table '{table_name}' in schema '{schema}'."
        )

        return result

    def inspect_view(
        self, schema: str, view_name: str
    ) -> Sequence[schemas.DatabaseEntity]:
        """
        Inspect a view, i.e. return its columns.
        """
        logger.debug(f"Inspecting view '{view_name}' in schema '{schema}'.")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.inspector is not None

        columns = self.inspector.get_columns(
            table_name=view_name, schema=schema
        )

        result = []
        for column in columns:
            result.append(
                schemas.DatabaseEntity(
                    name=column["name"],
                    type=schemas.DatabaseEntityType.column,
                    dbschema=schema,
                    datatype=str(column["type"] or ""),
                    nullable=column["nullable"] or True,
                )
            )

        result = sorted(result, key=lambda x: x.name)

        logger.debug(
            f"Successfully inspected view '{view_name}' in schema '{schema}'."
        )

        return result

    def fetch_preview(
        self, schema: str, name: str
    ) -> Sequence[schemas.DatabaseEntity]:
        """
        Fetch a preview of a table's or view's data.
        """
        logger.debug(f"Fetching preview of '{name}' in schema '{schema}'.")

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.connection is not None
        assert isinstance(self.config, schemas.DatabaseConfig)

        metadata = sqlalchemy.MetaData()
        table = sqlalchemy.Table(
            name,
            metadata,
            autoload_with=self.engine,
            schema=schema,
        )

        if self.config.fetch_limit > 0:
            query = table.select().limit(self.config.fetch_limit)
        else:
            query = table.select()

        query_result = self.connection.execute(query)

        rows = [
            {
                k: ("(bytes)" if isinstance(v, bytes) else v)
                for k, v in row.items()
            }
            for row in query_result.mappings()
        ]

        result = [
            schemas.DatabaseEntity(
                name=f"row {index}",
                type=schemas.DatabaseEntityType.row,
                data=row,
            )
            for index, row in enumerate(rows)
        ]

        logger.debug(
            f"Successfully fetched preview of '{name}' in schema '{schema}'."
        )

        return result

    def execute_query(
        self, query: str
    ) -> Tuple[Sequence[schemas.DatabaseEntity], int]:
        """
        Execute a SQL query and return the results as a tuple of a result
        sequence and an affected row count.
        """
        logger.debug(
            f"Executing query: {services.shorten_string(query, max_length=50)}"
        )

        if not self.connected:
            raise Exception("Not connected to a database.")

        assert self.connection is not None

        query_result = self.connection.execute(sqlalchemy.text(query))

        if query_result.returns_rows:
            rows = [
                {
                    k: ("(bytes)" if isinstance(v, bytes) else v)
                    for k, v in row.items()
                }
                for row in query_result.mappings()
            ]

            result = [
                schemas.DatabaseEntity(
                    name=f"row {index}",
                    type=schemas.DatabaseEntityType.row,
                    data=row,
                )
                for index, row in enumerate(rows)
            ]

            affected_rows = 0
        else:
            result = []
            affected_rows = query_result.rowcount or 0

        self.connection.commit()

        self.inspector = sqlalchemy.inspect(self.engine)

        logger.debug("Successfully executed query.")

        return (result, affected_rows)
