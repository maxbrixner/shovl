import datetime
import enum
from typing import Optional

import pydantic

from .service import ServiceEntity


class BucketEntityType(enum.Enum):
    """
    The type of an entity in the bucket.
    """

    bucket = "Bucket"
    file = "File"
    folder = "Folder"


class BucketEntity(ServiceEntity):
    """
    Represents an entity in a bucket.
    """

    last_modified: Optional[datetime.datetime] = pydantic.Field(
        default=None,
        description="Last modified timestamp of the entity (only for files).",
    )
    name: str = pydantic.Field(description="Name of the entity.")
    size: Optional[int] = pydantic.Field(
        default=None,
        description="Size of the entity in bytes (only for files).",
    )
    type: BucketEntityType = pydantic.Field(description="Type of the entity.")
