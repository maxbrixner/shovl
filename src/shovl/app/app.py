import logging

from textual.app import App

from shovl import schemas, screens

logger = logging.getLogger(__name__)


class ShovlApp(App[None]):
    """
    The main application class for Shovl.
    """

    config: schemas.ConfigSchema

    def __init__(self, config: schemas.ConfigSchema) -> None:
        """
        Initialize the Shovl application with the given configuration.
        """
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        """
        Push the main screen on mount.
        """
        logger.info("Starting application...")

        try:
            self.theme = self.config.gui.theme
        except Exception as exception:
            logger.debug("Error setting theme.", exc_info=exception)
            self.theme = "tokyo-night"

        self.push_screen(screen=screens.ConnectionScreen(config=self.config))

        logger.info("Application startup complete.")
