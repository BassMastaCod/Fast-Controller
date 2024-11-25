from typing import Callable, Optional

from sqlmodel import Field, SQLModel


def docstring_format(**kwargs):
    def decorator(func: Callable):
        func.__doc__ = func.__doc__.format(**kwargs)
        return func
    return decorator


def paginated(superclass: type[SQLModel]):
    class OptionalPK(superclass, table=True): # table=True is a hack to make PK optional
        pass
    class Paginated(OptionalPK):
        page: Optional[int] = Field(default=None, gt=0)
        per_page: Optional[int] = Field(default=None, gt=0)
    return Paginated
