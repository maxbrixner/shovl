import logging
import pathlib
from collections.abc import Callable, Sequence

import boto3  # type: ignore[import-untyped]
import botocore.client  # type: ignore[import-untyped]

from shovl import schemas, services

from .service import ServiceProvider

logger = logging.getLogger("shovl.providers.bucket")


class BucketProvider(ServiceProvider):
    """
    Bucket provider for connecting to and inspecting AWS S3 buckets using boto3.
    """

    temp_credentials: schemas.TemporaryCredentials | None

    session: boto3.Session | None
    client: botocore.client.BaseClient | None

    def _cleanup(self) -> None:
        """
        Cleanup the provider's state.
        """
        self.temp_credentials = None
        self.session = None
        self.client = None

    @property
    def connected(self) -> bool:
        """
        Check if the provider is connected to a bucket.
        """
        return self.session is not None or self.client is not None

    def connect(self) -> None:
        """
        Connect to a S3 bucket.
        """
        logger.info(f"Connecting to bucket: {self.config.name}")

        assert isinstance(self.config, schemas.BucketConfig)

        if self.connected:
            self.disconnect()

        self._create_session()

        if self.config.use_sts:
            self._get_temporary_credentials()

        self._create_s3_client()

        assert self.client is not None

        # Optionally test the connection by making a simple API call to the
        # bucket. This can be skipped, e.g. when the user does not have
        # permission to call head_bucket operation.
        if self.config.test_connection:
            self.client.head_bucket(  # type: ignore[reportUnknownMemberType]
                Bucket=services.resolve_credentials(self.config.bucket_name)
            )

        logger.info(
            f"Successfully connected to bucket: {self.config.name}. "
            f"Tested connection: {self.config.test_connection}"
        )

    def disconnect(self) -> None:
        """
        Disconnect from a S3 bucket.
        """
        logger.info(f"Disconnecting from bucket: {self.config.name}")

        if self.client:
            self.client.close()

        self._cleanup()

        logger.info(
            f"Successfully disconnected from bucket: {self.config.name}"
        )

    def inspect(
        self, prefix: str | None = None
    ) -> Sequence[schemas.BucketEntity]:
        """
        Inspect the contents of the S3 bucket at the given prefix.
        """
        logger.debug(
            f"Inspecting bucket: {self.config.name} with prefix: {prefix}"
        )

        if not self.connected:
            raise RuntimeError("Not connected to a bucket.")

        assert self.client is not None

        if prefix and not prefix.endswith("/"):
            raise RuntimeError("Prefix must end with a '/' character.")

        assert isinstance(self.config, schemas.BucketConfig)

        # If a prefix is provides, it already contains the head prefix.
        # If not, we need to use it as the prefix. This might be necessary
        # when a user does not have access to the root of the bucket, but
        # only to a specific prefix (e.g. a folder).
        if self.config.head_prefix and (not prefix or len(prefix) == 0):
            prefix = f"{self.config.head_prefix.rstrip('/')}/"

        paginator = self.client.get_paginator(  # type: ignore[reportUnknownMemberType]
            "list_objects_v2"
        )

        if prefix:
            page_iterator = paginator.paginate(  # type: ignore[reportUnknownMemberType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Prefix=prefix,
                Delimiter="/",
            )
        else:
            page_iterator = paginator.paginate(  # type: ignore[reportUnknownMemberType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Delimiter="/",
            )

        entities: list[schemas.BucketEntity] = []
        for page in page_iterator:  # type: ignore[reportUnknownVariableType]
            # "Folders" are found in CommonPrefixes
            if "CommonPrefixes" in page:
                for obj in page["CommonPrefixes"]:  # type: ignore[reportUnknownVariableType]
                    entities.append(
                        schemas.BucketEntity(
                            name=obj["Prefix"],  # type: ignore[reportUnknownArgumentType]
                            type=schemas.BucketEntityType.folder,
                        )
                    )

            # Top-level files (if any) are found in 'Contents'
            if "Contents" in page:
                for obj in page["Contents"]:  # type: ignore[reportUnknownVariableType]
                    if obj["Key"].endswith("/"):  # type: ignore[reportUnknownArgumentType]
                        continue
                    entities.append(
                        schemas.BucketEntity(
                            name=obj["Key"],  # type: ignore[reportUnknownArgumentType]
                            size=obj["Size"],  # type: ignore[reportUnknownArgumentType]
                            last_modified=obj["LastModified"],  # type: ignore[reportUnknownArgumentType]
                            type=schemas.BucketEntityType.file,
                        )
                    )

        # we sort the entities so that folders are always listed before files,
        # and then sort alphabetically by name (case-insensitive)
        entities = sorted(
            entities,
            key=lambda e: (
                0 if e.type == schemas.BucketEntityType.folder else 1,
                e.name.lower(),
            ),
        )

        logger.debug(
            f"Found {len(entities)} entities in bucket: {self.config.name} "
            f"with prefix: {prefix}"
        )
        return entities

    def download(
        self,
        key: str,
        target: pathlib.Path,
        recursive: bool = True,
        progress_callback: Callable[[int, int], None] = lambda x, y: None,
    ) -> None:
        """
        Download a file from the S3 bucket with the given key.
        """
        logger.info(
            f"Downloading from bucket: {self.config.name} with key: {key}"
        )

        self.abort_event.clear()

        if not self.connected:
            raise RuntimeError("Not connected to a bucket.")

        assert self.client is not None
        assert isinstance(self.config, schemas.BucketConfig)

        # List bucket entites
        if recursive:
            entities = self.client.list_objects_v2(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Prefix=key,
            )
        else:
            entities = self.client.list_objects_v2(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Prefix=key,
                Delimiter="/",
            )

        if "Contents" not in entities:
            return

        entities = entities["Contents"]  # type: ignore[reportUnknownArgumentType]

        # Filter out "folders" (keys that end with "/") and get the list of
        # files to download
        files: list[str] = [
            entity["Key"]
            for entity in entities  # type: ignore[reportUnknownVariableType]
            if "Key" in entity and not entity["Key"].endswith("/")  # type: ignore[reportUnknownArgumentType]
        ]

        # Get the parent directory of the S3 key. We want to remove the path
        # up to the parent directory from the S3 key when downloading,
        # so that we don't end up with a local directory structure that
        # includes the full S3 key path.
        # "file.ext" -> ""
        # "folder/file.ext" -> "folder"
        # "folder/subfolder/file.ext" -> "folder/subfolder"
        # "folder/" -> ""
        # "folder/subfolder/" -> "folder"
        parent = str(pathlib.Path(key).parent)
        if parent == ".":
            parent = ""

        for index, file in enumerate(files):
            if self.abort_event.is_set():
                logger.info(
                    f"Download aborted by user after downloading {index} files."
                )
                return

            progress_callback(index + 1, len(files))

            relative_path = file[len(parent) :].lstrip("/")
            local_filename = target / relative_path

            if not local_filename.parent.exists():
                local_filename.parent.mkdir(parents=True, exist_ok=True)

            self.client.download_file(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Key=file,
                Filename=str(local_filename),
            )

        logger.info(
            f"Successfully downloaded from bucket: {self.config.name} with "
            f"key: {key} to target: {target}"
        )

    def upload(
        self,
        key: str,
        source: pathlib.Path,
        recursive: bool = True,
        progress_callback: Callable[[int, int], None] = lambda x, y: None,
    ) -> None:
        """
        Upload files to the S3 bucket at the given key.
        """
        logger.info(
            f"Uploading to bucket: {self.config.name} with key: {key} from "
            f"source: {source}"
        )

        self.abort_event.clear()

        if not self.connected:
            raise RuntimeError("Not connected to a bucket.")

        if not source.exists():
            raise FileNotFoundError(f"Source path '{source}' does not exist.")

        assert self.client is not None
        assert isinstance(self.config, schemas.BucketConfig)

        # Find all local files to upload
        if source.is_file():
            entities = [source]
        elif recursive:
            entities = pathlib.Path(source).rglob("*")
        else:
            entities = pathlib.Path(source).glob("*")

        entities = [entity for entity in list(entities) if entity.is_file()]

        for index, entity in enumerate(list(entities)):
            if self.abort_event.is_set():
                logger.info(
                    f"Upload aborted by user after uploading {index} files."
                )
                return

            progress_callback(index + 1, len(entities))

            relative_path = entity.relative_to(source.parent)

            if key:
                s3_key = f"{key.rstrip('/')}/{relative_path.as_posix()}"
            else:
                s3_key = relative_path.as_posix()

            self.client.upload_file(  # type: ignore[reportUnknownArgumentType]
                Filename=str(entity),
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Key=s3_key,
            )

        logger.info(
            f"Successfully uploaded to bucket: {self.config.name} with key: "
            f"{key} from source: {source}"
        )

    def delete(
        self,
        key: str,
        recursive: bool = True,
        progress_callback: Callable[[int, int], None] = lambda x, y: None,
    ) -> None:
        """
        Delete a file from the S3 bucket with the given key.
        """
        logger.info(f"Deleting from bucket: {self.config.name} with key: {key}")

        self.abort_event.clear()

        if not self.connected:
            raise RuntimeError("Not connected to a bucket.")

        assert self.client is not None
        assert isinstance(self.config, schemas.BucketConfig)

        if recursive:
            entities = self.client.list_objects_v2(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Prefix=key,
            )
        else:
            entities = self.client.list_objects_v2(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Prefix=key,
                Delimiter="/",
            )

        if "Contents" not in entities:
            return

        entities = entities["Contents"]  # type: ignore[reportUnknownArgumentType]

        files: list[str] = [
            entity["Key"]
            for entity in entities  # type: ignore[reportUnknownArgumentType]
            if "Key" in entity and not entity["Key"].endswith("/")  # type: ignore[reportUnknownArgumentType]
        ]

        for index, file in enumerate(files):
            if self.abort_event.is_set():
                logger.info(
                    f"Deletion aborted by user after deleting {index} files."
                )
                return

            progress_callback(index + 1, len(files))

            self.client.delete_object(  # type: ignore[reportUnknownArgumentType]
                Bucket=services.resolve_credentials(self.config.bucket_name),
                Key=file,
            )

        logger.info(
            f"Successfully deleted from bucket: {self.config.name} with key: "
            f"{key}"
        )

    def _create_session(self) -> None:
        """
        Create a boto3 session using the provided configuration.
        """
        logger.info("Creating AWS session...")

        assert isinstance(self.config, schemas.BucketConfig)

        self.session = boto3.Session(
            aws_access_key_id=services.resolve_credentials(
                self.config.aws_access_key_id
            )
            if self.config.aws_access_key_id
            else None,
            aws_secret_access_key=services.resolve_credentials(
                self.config.aws_secret_access_key
            )
            if self.config.aws_secret_access_key
            else None,
            region_name=services.resolve_credentials(self.config.region_name)
            if self.config.region_name
            else None,
            profile_name=services.resolve_credentials(self.config.profile_name)
            if self.config.profile_name
            else None,
            aws_account_id=services.resolve_credentials(
                self.config.aws_account_id
            )
            if self.config.aws_account_id
            else None,
        )

        logger.info("AWS session created successfully.")

    def _create_s3_client(self) -> None:
        """
        Create a boto3 bucket resource using the session.
        """
        logger.info("Creating S3 client...")

        if not self.session:
            raise RuntimeError("AWS session not created.")

        assert isinstance(self.config, schemas.BucketConfig)

        if not self.config.use_sts:
            self.client = self.session.client("s3")  # type: ignore[reportUnknownArgumentType]
        else:
            if not self.temp_credentials:
                raise RuntimeError("Temporary credentials not obtained.")

            self.client = boto3.client(  # type: ignore[reportUnknownArgumentType]
                "s3",
                aws_access_key_id=self.temp_credentials.access_key_id,
                aws_secret_access_key=self.temp_credentials.secret_access_key,
                aws_session_token=self.temp_credentials.session_token,
                region_name=services.resolve_credentials(
                    self.config.region_name
                )
                if self.config.region_name
                else None,
                endpoint_url=services.resolve_credentials(
                    self.config.endpoint_url
                )
                if self.config.endpoint_url
                else None,
                config=self.config.client_config
                if self.config.client_config
                else None,
            )

        logger.info("S3 client created successfully.")

    def _get_temporary_credentials(self) -> None:
        """
        Get temporary credentials for accessing the S3 bucket.
        """
        logger.debug("Fetching temporary credentials using AWS STS...")

        if not self.session:
            raise RuntimeError("AWS session not created.")

        assert isinstance(self.config, schemas.BucketConfig)

        account_id = (
            services.resolve_credentials(self.config.aws_account_id)
            if self.config.aws_account_id
            else None
        )

        role_name = (
            services.resolve_credentials(self.config.role_name)
            if self.config.role_name
            else None
        )

        sts = self.session.client(  # type: ignore[reportUnknownArgumentType]
            "sts",
            region_name=services.resolve_credentials(self.config.region_name)
            if self.config.region_name
            else None,
            endpoint_url=services.resolve_credentials(self.config.endpoint_url)
            if self.config.endpoint_url
            else None,
            config=self.config.client_config
            if self.config.client_config
            else None,
        )

        response = sts.assume_role(  # type: ignore[reportUnknownArgumentType]
            RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
            RoleSessionName="ShovlBucketProviderSession",
        )

        if "Credentials" not in response:
            raise RuntimeError(
                "Failed to assume AWS role for temporary credentials."
            )

        self.temp_credentials = schemas.TemporaryCredentials(
            **response["Credentials"]  # type: ignore[reportUnknownArgumentType]
        )

        logger.debug("Temporary credentials obtained successfully.")
