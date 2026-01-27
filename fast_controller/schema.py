from typing import Mapping

from daomodel import DAOModel
from str_case_util import Case

from fast_controller import Resource


class Schema(DAOModel):
    """Base class for schemas, to act as a label."""
    pass


def schemas(**kwargs):
    """Applies multiple schema decorators at once.

    Example:
        class UserInput(Schema):
            name: Identifier[str]
            email: Optional[str]
            password: str

        @schemas(
            input=UserInput,
            detailed_output={
                'name': str,
                'email': Optional[str],
                'last_seen': datetime
            }
        )
        class User(Resource):
            ...

    Each keyword corresponds to a schema role:
        default, input, update, output, detailed_output

    Values may be:
        - A Schema subclass
        - An inline schema definition: {field_name: type}

    Raises: AttributeError if applied to a class that does not define the
        expected setter method (e.g., not a Resource subclass or invalid schema role).
    """
    def decorator(cls):
        for schema_role, schema in kwargs.items():
            setter_name = f'set_{schema_role}_schema'
            if not hasattr(cls, setter_name):
                raise AttributeError(
                    f'{cls.__name__} does not support schema role "{schema_role}". '
                    f'Expected one of: default, input, update, output, detailed_output.'
                )
            decorator_fn = _schema_decorator_factory(schema_role)
            cls = decorator_fn(schema)(cls)
        return cls
    return decorator


InlineSchema = Mapping[str, type]


def _resolve_schema(schema: type[Schema]|InlineSchema, resource: type[Resource], suffix: str) -> type[Schema]:
    if isinstance(schema, Mapping):
        fields = {name: typ for name, typ in schema.items()}
        schema = type(
            f'{resource.__name__}{suffix}',
            (Schema,),
            {
                '__annotations__': fields,
                '__module__': resource.__module__,
            }
        )
    return schema


def _schema_decorator_factory(schema_role: str):
    setter_name = f"set_{schema_role}_schema"
    suffix = Case.CAPITAL_CAMEL_CASE.format(schema_role)

    def decorator(schema=None, **inline_fields):
        if inline_fields:
            if schema is not None:
                raise TypeError(
                    f"Schema decorator for role '{schema_role}' received both "
                    f"a schema argument and inline fields. Use one or the other."
                )
            schema = inline_fields

        if schema is None:
            raise TypeError(
                f"Schema decorator for role '{schema_role}' requires either "
                f"a Schema subclass or inline field definitions."
            )

        def wrapper(cls):
            if not hasattr(cls, setter_name):
                raise AttributeError(
                    f'Cannot apply schema role "{schema_role}" to {cls.__name__}. '
                    f'This decorator may only be used on Resource subclasses. '
                    f'Expected method "{setter_name}" to exist.'
                )
            setter = getattr(cls, setter_name)
            setter(_resolve_schema(schema, cls, suffix))
            return cls

        return wrapper
    return decorator


default_schema = _schema_decorator_factory('default')
input_schema = _schema_decorator_factory('input')
update_schema = _schema_decorator_factory('update')
output_schema = _schema_decorator_factory('output')
detailed_output_schema = _schema_decorator_factory('detailed_output')
