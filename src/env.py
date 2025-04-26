import os

import dotenv

dotenv.load_dotenv()


class NotSet:
    def __repr__(self):
        return '<NotSet>'


class EnvNotSetError(Exception):
    pass


NOTSET = NotSet()

TRUTHY_VALUES = ('true', '1', 't', 'on', 'y', 'yes')
FALSY_VALUES = ('false', '0', 'f', 'off', 'n', 'no')
VALID_BOOL_VALUES = TRUTHY_VALUES + FALSY_VALUES


def get_env(key: str, default=NOTSET):
    """
    Description:
        Get a value from the environment variable.
    Args:
        key: str: The name of the environment variable.
        default: Any: The default value to return if the environment variable
            is not set.
    Returns:
        Any: The value of the environment variable, or the default value if
            the environment variable is not set.
    """
    value = os.getenv(key)
    if value is None:
        if default is NOTSET:
            raise EnvNotSetError(f'{key} is not set')
        else:
            return str(default)
    return value


def get_bool_env(key: str, default: bool = False) -> bool:
    """
    Description:
        Get a boolean value from the environment variable.
    Args:
        key: str: The name of the environment variable.
        default: bool: The default value to return if the environment variable
            is not set.
    Returns:
        bool: The value of the environment variable, or the default value if
            the environment variable is not set.
    """
    value = str(get_env(key, default)).lower()
    if value in VALID_BOOL_VALUES:
        return value in TRUTHY_VALUES
    else:
        raise ValueError(f'Invalid value for {key}: {value}')


def get_int_env(key: str, default: int = NOTSET) -> int:
    """
    Description:
        Get an integer value from the environment variable.
    Args:
        key: str: The name of the environment variable.
        default: int: The default value to return if the environment variable
            is not set.
    Returns:
        int: The value of the environment variable, or the default value if
            the environment variable is not set.
    """
    return int(get_env(key, default))


def get_list_env(
    key: str, separator: str = ',', type: type = str, default=NOTSET
) -> list:
    """
    Description:
        Get a list of values from the environment variable.
    Args:
        key: str: The name of the environment variable.
        separator: str: The separator to use to split the environment variable
            value.
        default: Any: The default value to return if the environment variable
            is not set.
    Returns:
        list: The list of values from the environment variable, or the default
            value if the environment variable is not set.
    """
    try:
        list_str = get_env(key)
        return [type(item.strip()) for item in list_str.split(separator)]
    except EnvNotSetError as e:
        if default is NOTSET:
            raise e
        return list(default)


HTTP_HOST = get_env('HTTP_HOST')
SECRET_KEY = get_env('SECRET_KEY')
KEEP_ALIVE_TIMEOUT = get_int_env('KEEP_ALIVE_TIMEOUT', 300)


__all__ = [
    'EnvNotSetError',
    'get_env',
    'get_bool_env',
    'get_int_env',
    'get_list_env',
    'HTTP_HOST',
    'SECRET_KEY',
    'KEEP_ALIVE_TIMEOUT',
]
