from inspect import isclass
from typing import ClassVar, Any

from daomodel import DAOModel
from sqlmodel import SQLModel


def either(preferred: Any, default: type[SQLModel]) -> type[SQLModel]:
    """
    Returns the preferred type if present, otherwise the default type.

    :param preferred: The type to return if not None
    :param default: The type to return if the preferred is not a model
    :return: either the preferred type or the default type
    """
    return preferred if isclass(preferred) and issubclass(preferred, SQLModel) else default


class Resource(DAOModel):
    __abstract__ = True
    _default_schema: type[SQLModel]
    _search_schema: type[SQLModel]
    _input_schema: type[SQLModel]
    _update_schema: type[SQLModel]
    _output_schema: type[SQLModel]
    _detailed_output_schema: type[SQLModel]
    path: ClassVar[str]

    @classmethod
    def get_path(cls) -> str:
        return getattr(cls, "path", "/api/" + cls.normalized_name())

    @classmethod
    def validate(cls, column_name, value):
        return True

    @classmethod
    def get_base(cls) -> type[SQLModel]:
        return cls

    @classmethod
    def set_default_schema(cls, schema: type[SQLModel]) -> None:
        cls._default_schema = schema

    @classmethod
    def get_default_schema(cls) -> type[SQLModel]:
        return either(cls._default_schema, cls)

    @classmethod
    def set_search_schema(cls, schema: type[SQLModel]) -> None:
        cls._search_schema = schema

    @classmethod
    def get_search_schema(cls) -> type[SQLModel]:
        return either(cls._search_schema, cls.get_default_schema())

    @classmethod
    def set_input_schema(cls, schema: type[SQLModel]) -> None:
        cls._input_schema = schema

    @classmethod
    def get_input_schema(cls) -> type[SQLModel]:
        return either(cls._input_schema, cls.get_default_schema())

    @classmethod
    def set_update_schema(cls, schema: type[SQLModel]) -> None:
        cls._update_schema = schema

    @classmethod
    def get_update_schema(cls) -> type[SQLModel]:
        return either(cls._update_schema, cls.get_input_schema())

    @classmethod
    def set_output_schema(cls, schema: type[SQLModel]) -> None:
        cls._output_schema = schema

    @classmethod
    def get_output_schema(cls) -> type[SQLModel]:
        return either(cls._output_schema, cls.get_default_schema())

    @classmethod
    def set_detailed_output_schema(cls, schema: type[SQLModel]) -> None:
        cls._detailed_output_schema = schema

    @classmethod
    def get_detailed_output_schema(cls) -> type[SQLModel]:
        return either(cls._detailed_output_schema, cls.get_output_schema())
