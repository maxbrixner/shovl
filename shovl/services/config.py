import functools
import json
import pathlib
from typing import Optional

import shovl.schemas as schemas


@functools.lru_cache()
def get_configuration(
    path: Optional[pathlib.Path] = None,
) -> schemas.ConfigSchema:
    """
    Read the configuration from disk and return it as a ConfigSchema object.
    """
    default_paths = [
        pathlib.Path(".shovl"),
        pathlib.Path.home() / pathlib.Path(".shovl"),
    ]

    if not path:
        for default_path in default_paths:
            if default_path.is_file():
                path = default_path
                break

    if not path:
        return schemas.ConfigSchema()

    with path.open("r") as file:
        config_data = json.load(file)

    return schemas.ConfigSchema(**config_data)


def get_sample_configuration() -> schemas.ConfigSchema:
    """
    Create a sample configuration.
    """
    config = schemas.ConfigSchema()

    config.connections.append(
        schemas.DatabaseConfig(
            name="Sample SQLite Database",
            description="A sample SQLite connection",
            url="sqlite:///sample.db",
        )
    )

    config.connections.append(
        schemas.BucketConfig(
            name="Sample S3 Bucket",
            description="A sample S3 bucket connection",
            bucket_name="shovl-app-test-bucket",
            aws_access_key_id="{{TEST_BUCKET_ACCESS_KEY_ID}}",
            aws_secret_access_key="{{TEST_BUCKET_SECRET_ACCESS_KEY}}",
            region_name="{{TEST_BUCKET_REGION_NAME}}",
            aws_account_id="{{TEST_BUCKET_ACCOUNT_ID}}",
        )
    )

    return config
