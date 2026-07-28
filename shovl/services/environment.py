import pathlib
from typing import Optional

import dotenv

import shovl.schemas as schemas

from .strings import resolve_path


def load_env_file(
    config: schemas.ConfigSchema,
    path: Optional[pathlib.Path] = None,
) -> None:
    """
    Read the .env file and set environment variables.
    """
    if not path and config.env_file:
        path = resolve_path(config.env_file)

    if not path:
        return

    if not path.is_file():
        raise FileNotFoundError(f"No such file: '{path}'")

    dotenv.load_dotenv(dotenv_path=path)
