from datetime import datetime
from typing import Any, Optional

import pytest
from daomodel import DAOModel
from daomodel.fields import Unsearchable, Identifier, ReferenceTo
from daomodel.search_util import ConditionOperator
from daomodel.testing import labeled_tests
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel

from fast_controller import Resource, Controller
from fast_controller.resource import either
from fast_controller.schema import Schema


class Preferred(Schema):
    pass
class Default(DAOModel):
    pass

@labeled_tests({
    'Valid subclass of BaseModel': [
        (Preferred, Default, Preferred),
        (BaseModel, Default, BaseModel),
        (SQLModel, Default, SQLModel),
        (DAOModel, Default, DAOModel),
        (Resource, Default, Resource)
    ],
    'Invalid types fallback to default': [
        (None, Default, Default),
        (1, Default, Default),
        ('test', Default, Default),
        (Controller, Default, Default)
    ]
})
def test_either(preferred: Any, default: type[BaseModel], expected: type[BaseModel]):
    assert either(preferred, default) == expected


def test_get_path():
    class Class(Resource):
        pass
    assert Class.get_resource_path() == '/classes'


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


class Article(Resource, table=True):
    author_name: Identifier[Author]
    title: Identifier[str]
    content: Optional[str]


class Publisher(Resource, table=True):
    name: Identifier[str]

    class Meta:
        searchable_relations = {
            Book.title, Book.page_count, Book.publication_date,
            (Book, Author.name),
            (Book, Author.active)
        }


@pytest.mark.parametrize('resource_id', [
    'valid_id',
    'another-valid-id',
    'simple',
    'with_underscore',
    'with-dash'
])
def test_resource_metaclass__allowed_pk(daos, resource_id: str):
    daos[Publisher].create(resource_id)
    daos.assert_in_db(Publisher, resource_id)


@pytest.mark.parametrize('resource_id', [
    'invalid/id',
    'has?question',
    'has#hash',
    'path/to/resource',
    'query?param=value',
    'fragment#anchor'
])
def test_resource_metaclass__restricted_pk(daos, resource_id: str):
    with pytest.raises(IntegrityError):
        daos[Publisher].create(resource_id)


@pytest.mark.parametrize('author_name,title', [
    ('valid_author', 'valid_title'),
    ('author-with-dash', 'title-with-dash'),
    ('author_underscore', 'title_underscore'),
    ('simple', 'another-simple')
])
def test_resource_metaclass__composite_pk(daos, author_name: str, title: str):
    daos[Author].create(author_name)
    daos[Article].create(author_name, title)
    daos.assert_in_db(Article, author_name, title)


@pytest.mark.parametrize('author_name,title', [
    ('invalid/author', 'valid_title'),
    ('valid_author', 'invalid/title'),
    ('author?query', 'title'),
    ('author', 'title#fragment'),
    ('path/to/author', 'path/to/title')
])
def test_resource_metaclass__composite_pk_restricted(daos, author_name: str, title: str):
    daos[Author].create('valid_author')
    with pytest.raises(IntegrityError):
        daos[Article].create(author_name, title)


class Box(Resource, table=True):
    id: Identifier[int]
class Fox(Resource, table=True):
    id: Identifier[int]
class Dress(Resource, table=True):
    id: Identifier[int]
class Library(Resource, table=True):
    id: Identifier[int]
class Property(Resource, table=True):
    id: Identifier[int]
class Baby(Resource, table=True):
    id: Identifier[int]
class Man(Resource, table=True):
    id: Identifier[int]
class Woman(Resource, table=True):
    id: Identifier[int]
class Child(Resource, table=True):
    id: Identifier[int]
class Person(Resource, table=True):
    id: Identifier[int]
class Goose(Resource, table=True):
    id: Identifier[int]
class Moose(Resource, table=True):
    id: Identifier[int]
class Mouse(Resource, table=True):
    id: Identifier[int]
class Fish(Resource, table=True):
    id: Identifier[int]

@labeled_tests({
    '-s': [
        (Author, 'Authors'),
        (Book, 'Books'),
        (Publisher, 'Publishers')
    ],
    '-es': [
        (Box, 'Boxes'),
        (Fox, 'Foxes'),
        (Dress, 'Dresses')
    ],
    '-ies': [
        (Library, 'Libraries'),
        (Property, 'Properties'),
        (Baby, 'Babies')
    ],
    '-en': [
        (Man, 'Men'),
        (Woman, 'Women'),
        (Child, 'Children')
    ],
    'Completely new word': [
        (Person, 'People'),
        (Goose, 'Geese'),
        (Mouse, 'Mice')
    ],
    'No change': [
        (Moose, 'Moose'),
        (Fish, 'Fish')
    ]
})
def test_resource_name(resource: Resource, expected: str):
    assert resource.resource_name() == expected


class AuthorCountry(Resource, table=True):
    id: Identifier[int]
class PeoplePerson(Resource, table=True):
    id: Identifier[int]
class FishLip(Resource, table=True):
    id: Identifier[int]

@labeled_tests({
    '-s': [
        (Author, '/authors'),
        (Book, '/books'),
        (Publisher, '/publishers')
    ],
    'Other': [
        (Person, '/people'),
        (Goose, '/geese'),
        (Mouse, '/mice')
    ],
    'Multiple words': [
        (AuthorCountry, '/author_countries'),
        (PeoplePerson, '/people_people'),
        (FishLip, '/fish_lips')
    ]
})
def test_get_resource_path(resource: Resource, expected: str):
    assert resource.get_resource_path() == expected


@pytest.mark.skip(reason='unsure of purpose of validate override')
def test_validate():
    pass


def test_get_search_schema():
    actual = Publisher.get_search_schema()
    assert actual.__name__ == 'PublisherSearchSchema'

    class Expected(Schema):
        name: ConditionOperator[str]
        book_title: ConditionOperator[str]
        book_page_count: ConditionOperator[int]
        book_publication_date: ConditionOperator[datetime]
        author_name: ConditionOperator[str]
        author_active: ConditionOperator[bool]
    assert {k: str(v.annotation) for k, v in actual.model_fields.items()} == \
           {k: str(v.annotation) for k, v in Expected.model_fields.items()}


class AuthorPKSchema(Schema):
    name: str
class BookPKSchema(Schema):
    title: str
class PublisherPKSchema(Schema):
    name: str
class CompositePKModel(Schema):
    name: str
class ArticlePKSchema(Schema):
    author_name: str
    title: str

@labeled_tests({
    'Single column PK': [
        (Author, AuthorPKSchema),
        (Book, BookPKSchema),
        (Publisher, PublisherPKSchema)
    ],
    'Composite PK': [
        (Article, ArticlePKSchema)
    ]
})
def test_get_pk_schema(resource: Resource, expected: Schema):
    actual = resource.get_pk_schema()
    assert actual.__name__ == expected.__name__
    assert {k: str(v.annotation) for k, v in actual.model_fields.items()} == \
           {k: str(v.annotation) for k, v in expected.model_fields.items()}


@pytest.mark.parametrize('resource', [Author, Book, Publisher, Article, Box, Person, Moose, Fish])
def test_get_base(resource: type[Resource]):
    assert resource.get_base() == resource
