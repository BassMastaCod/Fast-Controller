import inspect

from fast_controller import docstring_format


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
