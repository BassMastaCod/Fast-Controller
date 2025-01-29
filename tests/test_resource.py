from typing import Any

import pytest
from daomodel import DAOModel
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
    class C(Resource):
        pass
    assert C.get_resource_path() == "/api/c"


# TODO - Not convinced on this design for schema definitions
def test_get_base_and_schemas():
    pass
