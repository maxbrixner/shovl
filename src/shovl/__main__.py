import json
import logging
import pathlib
import sys
import typing

import typer

from shovl import app, schemas, services

runner = typer.Typer()


logger = logging.getLogger("shovl")


@runner.command()
def run(
    config: typing.Annotated[
        pathlib.Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
    env: typing.Annotated[
        pathlib.Path | None,
        typer.Option(
            "--env",
            "-e",
            help="Path to .env file for environment variables",
        ),
    ] = None,
    sample_config: typing.Annotated[
        bool,
        typer.Option(
            "--sample-config",
            "-s",
            help="Print a sample config file",
        ),
    ] = False,
    config_schema: typing.Annotated[
        bool,
        typer.Option(
            "--config-schema",
            "-S",
            help="Print the configuration schema",
        ),
    ] = False,
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
    except Exception as exception:  # noqa: BLE001
        print(f"Error loading configuration: {exception}", file=sys.stderr)
        return

    try:
        services.load_env_file(config=config_data, path=env)
    except Exception as exception:  # noqa: BLE001
        print(f"Error loading .env file: {exception}", file=sys.stderr)
        return

    try:
        services.setup_logging(config=config_data.logging)
    except Exception as exception:  # noqa: BLE001
        print(f"Error setting up logging: {exception}", file=sys.stderr)
        return

    try:
        app.ShovlApp(config=config_data).run()
    except Exception as exception:
        print(f"Error running Shovl: {exception}", file=sys.stderr)
        logger.debug(f"Error running Shovl: {exception}", exc_info=True)
        return


def main() -> None:
    """
    Serves as an entry point for the application in pyproject.toml.
    """
    runner()
