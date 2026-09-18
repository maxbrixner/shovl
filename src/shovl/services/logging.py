import logging

from shovl import schemas

from .strings import resolve_path


def setup_logging(config: schemas.LoggingConfig) -> None:
    """
    Set up a file logger for the application.
    """
    logger = logging.getLogger("shovl")

    if not config.enabled:
        logger.addHandler(logging.NullHandler())
        return

    logger.setLevel(config.level)

    file_handler = logging.FileHandler(
        resolve_path(config.file), mode=config.mode, encoding="utf-8"
    )
    file_handler.setLevel(config.level)

    formatter = logging.Formatter("[%(levelname)-10s] %(message)s")

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
