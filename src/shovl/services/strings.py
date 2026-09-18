import datetime
import os
import pathlib
import re
import urllib.parse


def resolve_path(path: str) -> pathlib.Path:
    """
    Resolves a config path by expanding environment variables and user home
    directory.
    """
    path = resolve_credentials(path)
    if path.startswith("~/"):
        resolved_path = pathlib.Path.home() / pathlib.Path(path[2:])
    else:
        resolved_path = pathlib.Path(path)

    return resolved_path.resolve()


def resolve_credentials(template: str, parse_url: bool = False) -> str:
    """
    Resolves placeholders in the given template string with environment
    variable values. Placeholders are in the format {{VAR_NAME}}.
    """
    pattern = re.compile(r"\{\{(\w+)\}\}")

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        env_variable = os.getenv(var_name, match.group(0))
        if parse_url:
            env_variable = urllib.parse.quote_plus(env_variable)
        return env_variable

    return pattern.sub(replacer, template)


def shorten_string(text: str, max_length: int = 100) -> str:
    """
    Shortens a string, adding "..." if truncated.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def to_timestamp(text: str) -> datetime.datetime:
    """
    Converts a string to a datatime object.
    """
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")


def to_time_string(dt: datetime.datetime) -> str:
    """
    Converts a datetime object to a string.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_file_size(bytes: int) -> str:
    """
    Formats a file size in bytes to a human-readable string.
    """
    if bytes < 1024:
        return f"{bytes}B"
    elif bytes < 1024**2:
        return f"{bytes / 1024:.2f}KB"
    elif bytes < 1024**3:
        return f"{bytes / 1024**2:.2f}MB"
    elif bytes < 1024**4:
        return f"{bytes / 1024**3:.2f}GB"
    else:
        return f"{bytes / 1024**4:.2f}TB"
