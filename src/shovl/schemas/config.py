from typing import Union

import pydantic


class GuiConfig(pydantic.BaseModel):
    max_list_items: int = pydantic.Field(
        default=1000,
        description="Maximum number of entities to display in the UI. Set to "
        "0 for no limit.",
    )
    theme: str = pydantic.Field(
        default="tokyo-night",
        description="The name of a textual theme. "
        "See https://textual.textualize.io/guide/design/",
    )


class LoggingConfig(pydantic.BaseModel):
    enabled: bool = pydantic.Field(
        default=False, description="Enable or disable logging."
    )
    file: str = pydantic.Field(
        default="~/.shovl.log", description="Path to the log file."
    )
    level: str = pydantic.Field(
        default="INFO",
        description="Logging level. One of: DEBUG, INFO, WARNING, ERROR, "
        "CRITICAL.",
    )
    mode: str = pydantic.Field(
        default="w",
        description="File mode for logging. 'a' for append, 'w' for overwrite.",
    )


class ProviderConfig(pydantic.BaseModel):
    description: str = pydantic.Field(
        description="Short description of the connection."
    )
    name: str = pydantic.Field(description="Name of the connection.")


class DatabaseConfig(ProviderConfig):
    engine_parameters: dict | None = pydantic.Field(
        default=None,
        description="Additional parameters to pass to the SQLAlchemy engine. "
        "For example, {'isolation_level': 'REPEATABLE READ', 'connect_args': "
        "{'sslmode': 'require'}}",
    )
    fetch_limit: int = pydantic.Field(
        default=1000,
        description="Maximum number of rows to fetch from the database. Set to "
        "0 for no limit.",
    )
    url: str = pydantic.Field(description="Database connection URL.")


class BucketConfig(ProviderConfig):
    aws_access_key_id: str | None = pydantic.Field(
        default=None, description="AWS access key ID for S3 access."
    )
    aws_account_id: str | None = pydantic.Field(
        default=None, description="AWS account ID for STS access."
    )
    aws_secret_access_key: str | None = pydantic.Field(
        default=None, description="AWS secret access key for S3 access."
    )
    bucket_name: str = pydantic.Field(description="Name of the S3 bucket.")
    endpoint_url: str | None = pydantic.Field(
        default=None,
        description="Custom endpoint URL for S3 access. Useful for "
        "S3-compatible storage services.",
    )
    head_prefix: str | None = pydantic.Field(
        default=None,
        description="General prefix to use when listing objects in the bucket.",
    )
    profile_name: str | None = pydantic.Field(
        default=None, description="AWS profile name for S3 access."
    )
    region_name: str | None = pydantic.Field(
        default=None, description="AWS region name for S3 access."
    )
    role_name: str | None = pydantic.Field(
        default=None, description="AWS role name for STS access."
    )
    client_config: dict | None = pydantic.Field(
        default=None,
        description="Additional parameters to pass to the boto3 session, see "
        "https://docs.aws.amazon.com/botocore/latest/reference/config.html",
    )
    test_connection: bool = pydantic.Field(
        default=True,
        description="Whether to test the connection to the S3 bucket on "
        "startup.",
    )
    use_sts: bool = pydantic.Field(
        default=False,
        description="Whether to use AWS Security Token Service for temporary "
        "credentials. Requires a role name and AWS account ID if set to True.",
    )


ServiceConfig = Union[DatabaseConfig, BucketConfig]


class ConfigSchema(pydantic.BaseModel):
    connections: list[ServiceConfig] = pydantic.Field(
        default=[],
        description="List of connections to data sources.",
    )
    gui: GuiConfig = pydantic.Field(
        default=GuiConfig(), description="GUI configuration."
    )
    logging: LoggingConfig = pydantic.Field(
        default=LoggingConfig(), description="Logging configuration."
    )
    env_file: str | None = pydantic.Field(
        default=None,
        description="Path to a .env file to load environment variables from.",
    )
