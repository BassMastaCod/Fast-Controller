from inspect import isclass
from typing import Any

from daomodel import DAOModel
from daomodel.search_util import ConditionOperator
from pydantic import create_model, BaseModel
from str_case_util import Case

from fast_controller.util import inflect


def either(preferred: Any, default: type[BaseModel]) -> type[BaseModel]:
    """Returns the preferred type if present, otherwise the default type.

    :param preferred: The type to return if not None
    :param default: The type to return if the preferred is not a model
    :return: either the preferred type or the default type
    """
    return preferred if isclass(preferred) and issubclass(preferred, BaseModel) else default


def get_field_type(field) -> type:
    """Returns the equivalent type for the given field.

    :param field: The Column of a model
    :return: the Python type used to represent the DB Column value
    """
    return getattr(field.type, 'impl', field.type).python_type


class Resource(DAOModel):
    __abstract__ = True
    _default_schema: type[BaseModel]
    _input_schema: type[BaseModel]
    _update_schema: type[BaseModel]
    _output_schema: type[BaseModel]
    _detailed_output_schema: type[BaseModel]

    @classmethod
    def resource_name(cls):
        """Returns the name of this resource within an API.

        Unless overridden, a plural version of the doc_name is returned, e.g. `Books` for `Book`.

        :return: The Resource name
        """
        return inflect.plural(cls.doc_name())

    @classmethod
    def get_resource_path(cls) -> str:
        """Returns the URI path to this resource as defined by the 'path' class variable.

        A default value of `/api/{resource_name}` is returned unless overridden.

        :return: The URI path to be used for this Resource
        """
        return '/api/' + Case.SNAKE_CASE.format(cls.resource_name())

    @classmethod
    def validate(cls, column_name, value):
        return True

    @classmethod
    def get_search_schema(cls) -> type[BaseModel]:
        """Returns a BaseModel representing the searchable fields"""
        def get_field_name(field) -> str:
            """Constructs the field's name, optionally prepending the table name."""
            field_name = field.name
            if hasattr(field, 'class_') and field.class_ is not cls and hasattr(field, 'table') and field.table.name:
                field_name = f'{field.table.name}_{field_name}'
            return field_name
        fields = [field[-1] if isinstance(field, tuple) else field for field in cls.get_searchable_properties()]
        field_types = {
            get_field_name(field): (ConditionOperator[get_field_type(field)], None) for field in fields
        }
        return create_model(
            f'{cls.doc_name()}SearchSchema',
            **field_types
        )

    @classmethod
    def get_pk_schema(cls) -> type[BaseModel]:
        """Returns a BaseModel representing the primary key fields"""
        return create_model(
            f'{cls.doc_name()}PKSchema',
            **{field.name: (get_field_type(field), ...) for field in cls.get_pk()}
        )

    @classmethod
    def get_base(cls) -> type[BaseModel]:
        return cls

    @classmethod
    def set_default_schema(cls, schema: type[BaseModel]) -> None:
        cls._default_schema = schema

    @classmethod
    def get_default_schema(cls) -> type[BaseModel]:
        return either(cls._default_schema, cls)

    @classmethod
    def set_input_schema(cls, schema: type[BaseModel]) -> None:
        cls._input_schema = schema

    @classmethod
    def get_input_schema(cls) -> type[BaseModel]:
        return either(cls._input_schema, cls.get_default_schema())

    @classmethod
    def set_update_schema(cls, schema: type[BaseModel]) -> None:
        cls._update_schema = schema

    @classmethod
    def get_update_schema(cls) -> type[BaseModel]:
        return either(cls._update_schema, cls.get_input_schema())

    @classmethod
    def set_output_schema(cls, schema: type[BaseModel]) -> None:
        cls._output_schema = schema

    @classmethod
    def get_output_schema(cls) -> type[BaseModel]:
        return either(cls._output_schema, cls.get_default_schema())

    @classmethod
    def set_detailed_output_schema(cls, schema: type[BaseModel]) -> None:
        cls._detailed_output_schema = schema

    @classmethod
    def get_detailed_output_schema(cls) -> type[BaseModel]:
        return either(cls._detailed_output_schema, cls.get_output_schema())
