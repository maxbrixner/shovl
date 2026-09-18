import logging
import threading

from shovl import schemas

logger = logging.getLogger("shovl.providers")


class ServiceProvider:
    """
    Base class for service providers. Inherited by all service providers
    (e.g. database, bucket, etc.) to provide common functionality.
    """

    config: schemas.ServiceConfig

    abort_event: threading.Event

    def __init__(self, config: schemas.ServiceConfig) -> None:
        """
        Initialize the service provider.
        """
        self.config = config

        self.abort_event = threading.Event()

        self._cleanup()

    def _cleanup(self) -> None:
        """
        Cleanup the service provider's state.
        """
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        """
        Check if the provider is connected to the service.
        """
        raise NotImplementedError

    def connect(self) -> None:
        """
        Connect to the service.
        """
        raise NotImplementedError

    def disconnect(self) -> None:
        """
        Disconnect from the service.
        """
        raise NotImplementedError

    def abort_current_operation(self) -> None:
        """
        Abort the current operation (if applicable).
        """
        self.abort_event.set()
