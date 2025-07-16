from typing import Callable, get_type_hints, Optional

from sqlmodel import SQLModel


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


# TODO: Determine bast way to add test coverage
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
