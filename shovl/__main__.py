import json
import logging
import pathlib
import sys
from typing import Optional

import typer

import shovl.app as app
import shovl.schemas as schemas
import shovl.services as services

runner = typer.Typer()


logger = logging.getLogger("shovl")


@runner.command()
def run(
    config: Optional[pathlib.Path] = typer.Option(
        None,
        help="Path to configuration file",
    ),
    env: Optional[pathlib.Path] = typer.Option(
        None,
        help="Path to .env file for environment variables",
    ),
    sample_config: bool = typer.Option(
        False,
        help="Print a sample config file",
    ),
    config_schema: bool = typer.Option(
        False,
        help="Print the configuration schema",
    ),
) -> None:
    """
    Run the textual app.
    """
    if sample_config:
        print(
            services.get_sample_configuration().model_dump_json(indent=4),
            file=sys.stdout,
        )
        return

    if config_schema:
        print(
            json.dumps(schemas.ConfigSchema.model_json_schema(), indent=4),
            file=sys.stdout,
        )
        return

    try:
        config_data = services.get_configuration(path=config)
    except Exception as exception:
        print(f"Error loading configuration: {exception}", file=sys.stderr)
        return

    try:
        services.load_env_file(config=config_data, path=env)
    except Exception as exception:
        print(f"Error loading .env file: {exception}", file=sys.stderr)
        return

    try:
        services.setup_logging(config=config_data.logging)
    except Exception as exception:
        print(f"Error setting up logging: {exception}", file=sys.stderr)
        return

    try:
        app.ShovlApp(config=config_data).run()
    except Exception as exception:
        print(f"Error running Shovl: {exception}", file=sys.stderr)
        logger.exception(f"Error running Shovl: {exception}")
        return


def main() -> None:
    """
    Serves as an entry point for the application in pyproject.toml.
    """
    runner()


if __name__ == "__main__":
    main()
