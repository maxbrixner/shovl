from typing import Optional

import pydantic


class ServiceEntity(pydantic.BaseModel):
    """
    Base entity model for services. Represents a generic entity in a service,
    such as a file, folder, or table. This model can be extended by specific
    service models to include additional fields relevant to that service.
    """

    name: str = pydantic.Field(description="Name of the entity.")


class HistoryItem(pydantic.BaseModel):
    """
    Represents a single item in the go-back history of Shovl.
    """

    entity: ServiceEntity = pydantic.Field(
        description="The entity associated with this history item."
    )
    filter: str = pydantic.Field(
        default="",
        description="The filter that was applied when this history item was "
        "created.",
    )
    selected_row: Optional[int] = pydantic.Field(
        default=None,
        description="The index of the selected row when this history item was "
        "created.",
    )
