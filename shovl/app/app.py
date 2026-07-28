import logging

from textual.app import App

import shovl.schemas as schemas
import shovl.screens as screens

logger = logging.getLogger("shovl.app")


class ShovlApp(App):
    """
    The main application class for Shovl.
    """

    # ENABLE_COMMAND_PALETTE = False

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
            logger.exception(f"Error setting theme: {exception}")
            self.theme = "tokyo-night"

        self.push_screen(screen=screens.ConnectionScreen(config=self.config))

        logger.info("Application startup complete.")
