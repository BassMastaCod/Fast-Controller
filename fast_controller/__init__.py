from enum import Enum, auto
from typing import Optional, Callable, Annotated

from daomodel import DAOModel
from daomodel.dao import NotFound
from daomodel.db import create_engine, DAOFactory
from daomodel.util import names_of
from fastapi import FastAPI, APIRouter, Depends, Path, Body, Query, Header
from fastapi.openapi.models import Response

from fast_controller.resource import Resource
from fast_controller.util import docstring_format


SessionLocal = create_engine()
def get_daos() -> DAOFactory:
    """Yields a DAOFactory."""
    with DAOFactory(SessionLocal) as daos:
        yield daos


class Action(Enum):
    VIEW = auto()
    SEARCH = auto()
    CREATE = auto()
    UPSERT = auto()
    MODIFY = auto()
    RENAME = auto()
    DELETE = auto()


class Controller:
    def __init__(self, app: Optional[FastAPI] = None):
        self.app = app

    def init_app(self, app: FastAPI) -> None:
        self.app = app

    # todo : define both ways to define apis
    @classmethod
    def create_api_group(cls,
            resource: Optional[type[Resource]] = None,
            prefix: Optional[str] = None,
            skip: Optional[set[Action]] = None) -> APIRouter:
        api_router = APIRouter(prefix=prefix if prefix else resource.get_resource_path(),
                               tags=[resource.doc_name()] if resource else None)
        if resource:
            cls.__register_resource_endpoints(api_router, resource, skip)
        return api_router

    def register_resource(self,
            resource: type[Resource],
            skip: Optional[set[Action]] = None,
            additional_endpoints: Optional[Callable] = None) -> None:
        api_router = APIRouter(prefix=resource.get_resource_path(), tags=[resource.doc_name()])
        self.__register_resource_endpoints(api_router, resource, skip)
        if additional_endpoints:
            additional_endpoints(api_router)
        self.app.include_router(api_router)

    @classmethod
    def __register_resource_endpoints(cls,
            router: APIRouter,
            resource: type[Resource],
            skip: Optional[set[Action]] = None) -> None:
        if skip is None:
            skip = set()
        if Action.SEARCH not in skip:
            @router.get("/", response_model=list[resource.get_output_schema()])
            @docstring_format(resource=resource.doc_name())
            def search(response: Response,
                       filters: Annotated[resource.get_search_schema(), Query()],
                       x_page: Optional[int] = Header(default=None, gt=0),
                       x_per_page: Optional[int] = Header(default=None, gt=0),
                       daos: DAOFactory = Depends(get_daos)) -> list[DAOModel]:
                """Searches for {resource} by criteria"""
                results = daos[resource].find(**filters.model_dump())
                response.headers["x-total-count"] = str(results.total)
                response.headers["x-page"] = str(results.page)
                response.headers["x-per-page"] = str(results.per_page)
                return results

        if Action.CREATE not in skip:
            @router.post("/", response_model=resource.get_detailed_output_schema(), status_code=201)
            @docstring_format(resource=resource.doc_name())
            def create(data: Annotated[resource.get_input_schema(), Query()],
                       daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                """Creates a new {resource}"""
                return daos[resource].create_with(**data.model_dump())

        if Action.UPSERT not in skip:
            @router.put("/", response_model=resource.get_detailed_output_schema())
            @docstring_format(resource=resource.doc_name())
            def upsert(data: Annotated[resource.get_input_schema(), Query()],
                       daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                """Creates/modifies a {resource}"""
                return daos[resource].upsert(**data.model_dump())

        pk = [p.name for p in resource.get_pk()]
        path = "/".join([""] + ["{" + p + "}" for p in pk])

        # Caveat: Only up to 5 columns are supported within a primary key.
        # This allows us to avoid resorting to exec() while **kwargs is unsupported for Path variables
        match len(pk):
            case 1:
                if Action.VIEW not in skip:
                    @router.get(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def view(pk0 = Path(alias=pk[0]),
                             daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Retrieves a detailed view of a {resource}"""
                        return daos[resource].get(pk0)

                # Caveat: Rename action is only supported for resources with a single column primary key
                if Action.RENAME not in skip:
                    @router.post(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def rename(pk0 = Path(alias=pk[0]),
                               new_id = Body(alias=pk[0]),
                               daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Renames a {resource}"""
                        current = daos[resource].get(pk0)
                        try:
                            existing = daos[resource].get(new_id)
                            # todo Set FKs
                            for fk in resource.get_fks():
                                fk = new_id
                            daos[resource].remove_model(current, commit=False)
                            current = existing
                        except NotFound:
                            for p in names_of(current.get_pk()):
                                setattr(current, p, new_id)
                                # todo Set entire PK
                        return daos[resource].update_model(current)

                # Caveat: Modify action is only supported for resources with a single column primary key
                # Use Upsert instead for multi-column PK resources
                if Action.MODIFY not in skip:
                    @router.put(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def update(data: Annotated[resource.get_update_schema(), Body()],  # TODO - Remove PK from input schema
                               pk0 = Path(alias=pk[0]),
                               daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Creates/modifies a {resource}"""
                        result = daos[resource].get(pk0)
                        result.copy_values(**data.model_dump())
                        return daos[resource].update(**result.model_dump())

                if Action.DELETE not in skip:
                    @router.delete(path, status_code=204)
                    @docstring_format(resource=resource.doc_name())
                    def delete(pk0 = Path(alias=pk[0]),
                               daos: DAOFactory = Depends(get_daos)) -> None:
                        """Deletes a {resource}"""
                        daos[resource].remove(pk0)

            case 2:
                if Action.VIEW not in skip:
                    @router.get(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def view(pk0 = Path(alias=pk[0]),
                             pk1 = Path(alias=pk[1]),
                             daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Retrieves a detailed view of a {resource}"""
                        return daos[resource].get(pk0, pk1)

                if Action.DELETE not in skip:
                    @router.delete(path, status_code=204)
                    @docstring_format(resource=resource.doc_name())
                    def delete(pk0 = Path(alias=pk[0]),
                               pk1 = Path(alias=pk[1]),
                               daos: DAOFactory = Depends(get_daos)) -> None:
                        """Deletes a {resource}"""
                        daos[resource].remove(pk0, pk1)

            case 3:
                if Action.VIEW not in skip:
                    @router.get(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def view(pk0 = Path(alias=pk[0]),
                             pk1 = Path(alias=pk[1]),
                             pk2 = Path(alias=pk[2]),
                             daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Retrieves a detailed view of a {resource}"""
                        return daos[resource].get(pk0, pk1, pk2)

                if Action.DELETE not in skip:
                    @router.delete(path, status_code=204)
                    @docstring_format(resource=resource.doc_name())
                    def delete(pk0 = Path(alias=pk[0]),
                               pk1 = Path(alias=pk[1]),
                               pk2 = Path(alias=pk[2]),
                               daos: DAOFactory = Depends(get_daos)) -> None:
                        """Deletes a {resource}"""
                        daos[resource].remove(pk0, pk1, pk2)

            case 4:
                if Action.VIEW not in skip:
                    @router.get(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def view(pk0 = Path(alias=pk[0]),
                             pk1 = Path(alias=pk[1]),
                             pk2 = Path(alias=pk[2]),
                             pk3 = Path(alias=pk[3]),
                             daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Retrieves a detailed view of a {resource}"""
                        return daos[resource].get(pk0, pk1, pk2, pk3)

                if Action.DELETE not in skip:
                    @router.delete(path, status_code=204)
                    @docstring_format(resource=resource.doc_name())
                    def delete(pk0 = Path(alias=pk[0]),
                               pk1 = Path(alias=pk[1]),
                               pk2 = Path(alias=pk[2]),
                               pk3 = Path(alias=pk[3]),
                               daos: DAOFactory = Depends(get_daos)) -> None:
                        """Deletes a {resource}"""
                        daos[resource].remove(pk0, pk1, pk2, pk3)

            case 5:
                if Action.VIEW not in skip:
                    @router.get(path, response_model=resource.get_detailed_output_schema())
                    @docstring_format(resource=resource.doc_name())
                    def view(pk0 = Path(alias=pk[0]),
                             pk1 = Path(alias=pk[1]),
                             pk2 = Path(alias=pk[2]),
                             pk3 = Path(alias=pk[3]),
                             pk4 = Path(alias=pk[4]),
                             daos: DAOFactory = Depends(get_daos)) -> DAOModel:
                        """Retrieves a detailed view of a {resource}"""
                        return daos[resource].get(pk0, pk1, pk2, pk3, pk4)

                if Action.DELETE not in skip:
                    @router.delete(path, status_code=204)
                    @docstring_format(resource=resource.doc_name())
                    def delete(pk0 = Path(alias=pk[0]),
                               pk1 = Path(alias=pk[1]),
                               pk2 = Path(alias=pk[2]),
                               pk3 = Path(alias=pk[3]),
                               pk4 = Path(alias=pk[4]),
                               daos: DAOFactory = Depends(get_daos)) -> None:
                        """Deletes a {resource}"""
                        daos[resource].remove(pk0, pk1, pk2, pk3, pk4)
