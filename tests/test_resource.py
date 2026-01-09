from datetime import datetime
from typing import Any, Optional

import pytest
from daomodel import DAOModel
from daomodel.fields import Unsearchable, Identifier, ReferenceTo
from daomodel.search_util import ConditionOperator
from sqlmodel import SQLModel

from fast_controller import Resource, Controller
from fast_controller.resource import either


class Preferred(SQLModel):
    pass


class Default(SQLModel):
    pass


@pytest.mark.parametrize("preferred, default, expected", [
    (Preferred, Default, Preferred),
    (SQLModel, Default, SQLModel),
    (DAOModel, Default, DAOModel),
    (Resource, Default, Resource),
    (None, Default, Default),
    (1, Default, Default),
    ("test", Default, Default),
    (Controller, Default, Default)
])
def test_either(preferred: Any, default: type[SQLModel], expected: type[SQLModel]):
    assert either(preferred, default) == expected


def test_get_path():
    class Class(Resource):
        pass
    assert Class.get_resource_path() == "/api/classes"


class Author(Resource, table=True):
    name: Identifier[str]
    bio: Optional[str]
    active: bool = True


class Book(Resource, table=True):
    title: Identifier[str]
    author_name: Author
    description: Unsearchable[Optional[str]]
    page_count: Optional[int]
    publication_date: Optional[datetime]
    publisher_name: str = ReferenceTo('publisher.name')


class Publisher(Resource, table=True):
    name: Identifier[str]

    class Meta:
        searchable_relations = {
            Book.title, Book.page_count, Book.publication_date,
            (Book, Author.name),
            (Book, Author.active)
        }


def test_get_search_schema():
    actual = Publisher.get_search_schema()
    assert actual.__name__ == 'PublisherSearchSchema'
    class Expected(SQLModel):
        name: ConditionOperator[str]
        book_title: ConditionOperator[str]
        book_page_count: ConditionOperator[int]
        book_publication_date: ConditionOperator[datetime]
        author_name: ConditionOperator[str]
        author_active: ConditionOperator[bool]
    assert {k: str(v.annotation) for k, v in actual.model_fields.items()} == \
           {k: str(v.annotation) for k, v in Expected.model_fields.items()}


# TODO - Not convinced on this design for schema definitions
def test_get_base_and_schemas():
    pass
