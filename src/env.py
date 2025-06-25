import os

import dotenv

dotenv.load_dotenv()


class NotSet:
    def __repr__(self) -> str:
        return "<NotSet>"


class EnvNotSetError(Exception):
    pass


NOTSET = NotSet()

TRUTHY_VALUES = ("true", "1", "t", "on", "y", "yes")
FALSY_VALUES = ("false", "0", "f", "off", "n", "no")
VALID_BOOL_VALUES = TRUTHY_VALUES + FALSY_VALUES


def get_env(key: str, default=NOTSET) -> str:
    """Get the value of an environment variable.

    Looks up the environment variable `key`. If it is not set and a `default`
    is provided, returns the default value as a string. If the variable is not
    set and no default is given, raises `EnvNotSetError`.

    Args:
        key (str): Name of the environment variable.
        default (Any): Value to return if the variable is not set. If not provided,
            an error is raised.

    Returns:
        str: The environment variable value or the default as a string.

    Raises:
        EnvNotSetError: If the variable is not set and no default is provided.

    """
    value = os.getenv(key)
    if value is None:
        if default is NOTSET:
            raise EnvNotSetError("%s is not set", key)
        return str(default)
    return value


def get_bool_env(key: str, *, default: bool = False) -> bool:
    """Get a boolean value from an environment variable.

    Converts the value of the environment variable `key` to a boolean.
    Accepted values are defined in `VALID_BOOL_VALUES`. If the variable is not set,
        returns the provided `default`.

    Args:
        key (str): Name of the environment variable.
        default (bool): Default value to use if the variable is not set.

    Returns:
        bool: Boolean representation of the environment variable value.

    Raises:
        ValueError: If the environment value is not a valid boolean string.

    """
    value = str(get_env(key, default)).lower()
    if value in VALID_BOOL_VALUES:
        return value in TRUTHY_VALUES
    raise ValueError("Invalid value for %s: %s", (key, value))


def get_int_env(key: str, default: int = NOTSET) -> int:
    """Get an integer value from an environment variable.

    Retrieves the value of the given environment variable `key`
        and converts it to an integer.
    If the variable is not set and `default` is provided,
        returns the default value instead.

    Args:
        key (str): Name of the environment variable.
        default (int): Default value if the environment variable is not set.

    Returns:
        int: The integer value of the environment variable or the default.

    """
    return int(get_env(key, default))


def get_list_env(
    key: str,
    separator: str = ",",
    type: type = str,  # noqa: A002
    default=NOTSET,
) -> list:
    """Get a list of values from an environment variable.

    This function retrieves the value of the environment variable `key`,
    splits it by the given `separator`, and casts each item to the given `type`.

    Args:
        key (str): Name of the environment variable.
        separator (str): Delimiter to split the environment value. Defaults to ",".
        type (type): Type to convert each list item to. Defaults to `str`.
        default (Any): Default value if the variable is not set. If not provided,
            raises `EnvNotSetError`.

    Returns:
        list: A list of converted values, or the default if not set.

    """
    try:
        list_str = get_env(key)
        return [type(item.strip()) for item in list_str.split(separator)]
    except EnvNotSetError:
        if default is NOTSET:
            raise
        return list(default)


HTTP_HOST = get_env("HTTP_HOST")
SECRET_KEY = get_env("SECRET_KEY")
KEEP_ALIVE_TIMEOUT = get_int_env("KEEP_ALIVE_TIMEOUT", 300)
CLOUDFLARE_SITE_KEY = get_env("CLOUDFLARE_SITE_KEY")
CLOUDFLARE_SECRET_KEY = get_env("CLOUDFLARE_SECRET_KEY")
CLOUDFLARE_API_URL = get_env("CLOUDFLARE_API_URL")


__all__ = [
    "CLOUDFLARE_API_URL",
    "CLOUDFLARE_SECRET_KEY",
    "CLOUDFLARE_SITE_KEY",
    "HTTP_HOST",
    "KEEP_ALIVE_TIMEOUT",
    "SECRET_KEY",
    "EnvNotSetError",
    "get_bool_env",
    "get_env",
    "get_int_env",
    "get_list_env",
]
