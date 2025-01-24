import inspect

from sqlmodel import SQLModel, Field, Relationship

from fast_controller import docstring_format, paginated, Resource


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


def test_paginated():
    class TestModel(SQLModel):
        a: str
        b: str
    result = paginated(TestModel)
    assert "a" in result.model_fields
    assert "b" in result.model_fields
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields


def test_paginated__table_true():
    class TestModel(SQLModel, table=True):
        a: str = Field(primary_key=True)
        b: str
    result = paginated(TestModel)
    assert "a" in result.model_fields
    assert "b" in result.model_fields
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields


def test_paginated__resource():
    class TestModel(Resource, table=True):
        a: str = Field(primary_key=True)
        b: str
    result = paginated(TestModel)
    assert "a" in result.model_fields
    assert "b" in result.model_fields
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields


def test_paginated__related():
    class ModelA(SQLModel, table=True):
        id: str = Field(primary_key=True)
        b: list['ModelB'] = Relationship(back_populates='a')
    class ModelB(SQLModel, table=True):
        id: str = Field(primary_key=True)
        a_id: str = Field(foreign_key="modela.id")
        a: ModelA = Relationship(back_populates='a')
    result = paginated(ModelA)
    assert "id" in result.model_fields
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields
    result = paginated(ModelB)
    assert "id" in result.model_fields
    assert "a_id" in result.model_fields
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields


def test_paginated__empty_model():
    class TestModel(SQLModel):
        pass
    result = paginated(TestModel)
    assert "page" in result.model_fields
    assert "per_page" in result.model_fields
