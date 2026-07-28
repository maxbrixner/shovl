import datetime

import pydantic


class TemporaryCredentials(pydantic.BaseModel):
    """
    Temporary AWS credentials, typically obtained from AWS STS (Security Token
    Service).
    """

    access_key_id: str = pydantic.Field(
        ...,
        alias="AccessKeyId",
        description="The access key ID of the temporary credentials.",
    )
    expiration: datetime.datetime = pydantic.Field(
        ...,
        alias="Expiration",
        description="The expiration time of the temporary credentials.",
    )
    secret_access_key: str = pydantic.Field(
        ...,
        alias="SecretAccessKey",
        description="The secret access key of the temporary credentials.",
    )
    session_token: str = pydantic.Field(
        ...,
        alias="SessionToken",
        description="The session token of the temporary credentials.",
    )
