import inspect
from functools import wraps
from typing import Callable, get_type_hints
from warnings import deprecated

import inflect as _inflect
from daomodel.search_util import *
from fastapi import Response
from sqlmodel import SQLModel


inflect = _inflect.engine()


class InvalidInput(Exception):
    """Indicates that the user provided bad input."""
    def __init__(self, detail: str):
        self.detail = detail


def docstring_format(**kwargs):
    """
    A decorator that formats the docstring of a function with specified values.

    :param kwargs: The values to inject into the docstring
    """
    def decorator(func: Callable):
        func.__doc__ = func.__doc__.format(**kwargs)
        return func
    return decorator


@deprecated("No usages and no test coverage")
def all_optional(superclass: type[SQLModel]):
    """Creates a new SQLModel for the specified class but having no required fields.

    :param superclass: The SQLModel of which to make all fields Optional
    :return: The newly wrapped Model
    """
    class OptionalModel(superclass):
        pass
    for field, field_type in get_type_hints(OptionalModel).items():
        if not isinstance(field_type, type(Optional)):
            OptionalModel.__annotations__[field] = Optional[field_type]
    return OptionalModel


def expose_path_params(func: Callable, field_names: list[str]) -> Callable:
    """Converts implicit path parameters from **kwargs to explicit parameters.

    Takes a function using **kwargs and modifies its signature to expose specific
    field names as explicit path parameters (field1, field2, etc.) with Path defaults,
    making them visible to FastAPI's routing system. All existing parameters
    (except **kwargs) are preserved in their original order.e

    :param func: The function to modify
    :param field_names: List of field names to expose as path parameters
    :return: The modified function with an updated signature
    """
    sig = inspect.signature(func)
    new_params = []

    for field_name in field_names:
        new_params.append(inspect.Parameter(
            field_name,
            inspect.Parameter.POSITIONAL_OR_KEYWORD
        ))

    for param_name, param in sig.parameters.items():
        if param.kind != inspect.Parameter.VAR_KEYWORD:
            new_params.append(param)

    func.__signature__ = sig.replace(parameters=new_params)
    return func


def extract_values(kwargs: dict, field_names: list[str]) -> list:
    """Extracts values from kwargs in the specified order.

    :param kwargs: Dictionary containing the function arguments
    :param field_names: List of field names in the desired order
    :return: List of values in the same order as field_names
    """
    return [kwargs[field] for field in field_names]


def cache_control(value: str):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                response = await func(*args, **kwargs)
                if isinstance(response, Response):
                    response.headers['Cache-Control'] = value
                return response
            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                response = func(*args, **kwargs)
                if isinstance(response, Response):
                    response.headers['Cache-Control'] = value
                return response
            return wrapper

    return decorator


immutable = cache_control('public, max-age=31536000, immutable')
no_cache = cache_control('no-store')
cache_1h = cache_control('public, max-age=3600')
