import enum
from typing import Dict, Optional

import pydantic

from .service import ServiceEntity


class DatabaseEntityType(enum.Enum):
    """
    The type of an entity in the database.
    """

    column = "Column"
    row = "Row"
    schema = "Schema"
    schemas = "Schemas"
    table = "Table"
    tables = "Tables"
    view = "View"
    views = "Views"


class DatabaseEntity(ServiceEntity):
    """
    Represents an entity in a database.
    """

    data: Optional[Dict] = pydantic.Field(
        default=None, description="Data of the row (only for rows)."
    )
    datatype: Optional[str] = pydantic.Field(
        default=None, description="Data type of the column (only for columns)."
    )
    dbschema: Optional[str] = pydantic.Field(
        default=None, description="Parent schema of the entity."
    )
    nullable: Optional[bool] = pydantic.Field(
        default=None,
        description="Whether the column is nullable (only for columns).",
    )
    type: DatabaseEntityType = pydantic.Field(description="Type of the entity.")
