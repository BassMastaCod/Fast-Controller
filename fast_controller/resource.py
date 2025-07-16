from inspect import isclass
from typing import Any

from daomodel import DAOModel
from pydantic import create_model
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
    _input_schema: type[SQLModel]
    _update_schema: type[SQLModel]
    _output_schema: type[SQLModel]
    _detailed_output_schema: type[SQLModel]

    @classmethod
    def get_resource_path(cls) -> str:
        """
        Returns the URI path to this resource as defined by the 'path' class variable.
        A default value of `/api/{resource_name} is returned unless overridden.

        :return: The URI path to be used for this Resource
        """
        return "/api/" + cls.normalized_name()

    @classmethod
    def validate(cls, column_name, value):
        return True

    @classmethod
    def get_search_schema(cls) -> type[SQLModel]:
        """Returns an SQLModel representing the searchable fields"""
        def get_field_name(field) -> str:
            """Constructs the field's name, optionally prepending the table name."""
            field_name = field.name
            if hasattr(field, 'class_') and field.class_ is not cls and hasattr(field, 'table') and field.table.name:
                field_name = f'{field.table.name}_{field_name}'
            return field_name
        def get_field_type(field) -> type:
            field_type = field.type
            if hasattr(field_type, 'impl'):
                field_type = field_type.impl
            return field_type.python_type
        fields = [field[-1] if isinstance(field, tuple) else field for field in cls.get_searchable_properties()]
        field_types = {
            get_field_name(field): (get_field_type(field), None) for field in fields
        }
        return create_model(
            f'{cls.doc_name()}SearchSchema',
            **field_types
        )

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
