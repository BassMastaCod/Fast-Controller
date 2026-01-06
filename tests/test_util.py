import inspect
from unittest.mock import Mock

from daomodel.search_util import *

from fast_controller import docstring_format
from fast_controller.util import expose_path_params, extract_values, to_condition_operator


@docstring_format(key="value")
def test_docstring_format():
    """{key}"""
    assert inspect.getdoc(test_docstring_format) == "value"


@docstring_format(key="value")
def test_docstring_format__empty():
    """"""
    assert inspect.getdoc(test_docstring_format__empty) == ""


@docstring_format(key="value")
def test_docstring_format__multiple_values():
    """{key}1, {key}2"""
    assert inspect.getdoc(test_docstring_format__multiple_values) == "value1, value2"


@docstring_format(key1="value1", key2="value2")
def test_docstring_format__multiple_keys():
    """{key1}, {key2}"""
    assert inspect.getdoc(test_docstring_format__multiple_keys) == "value1, value2"


# TODO: Convert to labeled_tests
def test_expose_path_params():
    def test_func(**kwargs):
        return kwargs

    modified_func = expose_path_params(test_func, ["id"])
    sig = inspect.signature(modified_func)

    assert list(sig.parameters.keys()) == ["id"]


def test_expose_path_params__multiple_params():
    def test_func(**kwargs):
        pass

    modified_func = expose_path_params(test_func, ["field1", "field2", "field3"])
    sig = inspect.signature(modified_func)

    assert list(sig.parameters.keys()) == ["field1", "field2", "field3"]


def test_expose_path_params__no_params():
    def test_func(**kwargs):
        pass

    modified_func = expose_path_params(test_func, [])
    sig = inspect.signature(modified_func)

    assert list(sig.parameters.keys()) == []


def test_expose_path_params__existing_params():
    def test_func(model: str = "default_model", daos: Mock = Mock(), **kwargs):
        pass

    modified_func = expose_path_params(test_func, ["user_id", "role_id"])
    sig = inspect.signature(modified_func)

    assert list(sig.parameters.keys()) == ["user_id", "role_id", "model", "daos"]

    assert sig.parameters["model"].annotation == str
    assert sig.parameters["model"].default == "default_model"
    assert sig.parameters["daos"].annotation == Mock
    assert isinstance(sig.parameters["daos"].default, Mock)


def test_expose_path_params__original_preserved():
    def test_func(**kwargs):
        return kwargs

    modified_func = expose_path_params(test_func, ["field1"])

    assert modified_func is test_func

    result = test_func(field1="test_value")
    assert result["field1"] == "test_value"


def test_extract_values():
    kwargs = {
        "field1": "value1",
        "field2": "value2",
        "field3": "value3"
    }
    field_names = ["field1", "field2", "field3"]
    expected = ["value1", "value2", "value3"]

    assert extract_values(kwargs, field_names) == expected


def test_extract_values___order():
    kwargs = {
        "field1": "value1",
        "field2": "value2",
        "field3": "value3"
    }
    field_names = ["field3", "field1", "field2"]
    expected = ["value3", "value1", "value2"]

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__single_field():
    kwargs = {"id": "test_id"}
    field_names = ["id"]

    result = extract_values(kwargs, field_names)
    assert result == ["test_id"]


def test_extract_values__matching_values():
    kwargs = {
        "field1": "value",
        "field2": "value"
    }
    field_names = ["field1", "field2"]
    expected = ["value", "value"]

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__duplicated_field():
    kwargs = {
        "field1": "value1",
        "field2": "value2"
    }
    field_names = ["field1", "field1", "field2", "field1"]
    expected = ["value1", "value1", "value2", "value1"]

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__partial_extract():
    kwargs = {
        "field1": "value1",
        "field2": "value2",
        "extra1": "ignored",
        "extra2": "ignored",
    }
    field_names = ["field1", "field2"]
    expected = ["value1", "value2"]

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__no_fields():
    kwargs = {"field": "value"}
    field_names = []
    expected = []

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__empty():
    kwargs = {}
    field_names = []
    expected = []

    assert extract_values(kwargs, field_names) == expected


def test_extract_values__different_types():
    kwargs = {
        "string_field": "string_value",
        "int_field": 123,
        "bool_field": True,
        "list_field": [1, 2, 3],
        "none_field": None
    }
    field_names = ["string_field", "int_field", "bool_field", "list_field", "none_field"]
    expected = ["string_value", 123, True, [1, 2, 3], None]

    assert extract_values(kwargs, field_names) == expected


def test_to_condition_operator__equals():
    op = to_condition_operator("value")
    assert isinstance(op, Equals)
    assert op.values == ("value",)

    op = to_condition_operator("is:value")
    assert isinstance(op, Equals)
    assert op.values == ("value",)


def test_to_condition_operator__lt():
    op = to_condition_operator("lt:5")
    assert isinstance(op, LessThan)
    assert op.values == ("5",)


def test_to_condition_operator__le():
    op = to_condition_operator("le:5")
    assert isinstance(op, LessThanEqualTo)
    assert op.values == ("5",)


def test_to_condition_operator__gt():
    op = to_condition_operator("gt:5")
    assert isinstance(op, GreaterThan)
    assert op.values == ("5",)


def test_to_condition_operator__ge():
    op = to_condition_operator("ge:5")
    assert isinstance(op, GreaterThanEqualTo)
    assert op.values == ("5",)


def test_to_condition_operator__between():
    op = to_condition_operator("between:1|5")
    assert isinstance(op, Between)
    assert op.values == ("1", "5")


def test_to_condition_operator__anyof():
    op = to_condition_operator("anyof:1|2|3")
    assert isinstance(op, AnyOf)
    assert op.values == ("1", "2", "3")


def test_to_condition_operator__noneof():
    op = to_condition_operator("noneof:1|2|3")
    assert isinstance(op, NoneOf)
    assert op.values == ("1", "2", "3")


def test_to_condition_operator__isset():
    assert isinstance(to_condition_operator("is:set"), IsSet)


def test_to_condition_operator__notset():
    assert isinstance(to_condition_operator("is:notset"), NotSet)


def test_to_condition_operator__part():
    op = to_condition_operator("part_is:value")
    assert isinstance(op, Equals)
    assert op.values == ("value",)
    assert op.part == "part"
