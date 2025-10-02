from contextlib import contextmanager
from enum import Enum, auto
from typing import Optional, Callable
import inspect

from daomodel import DAOModel
from daomodel.dao import NotFound
from daomodel.db import DAOFactory
from daomodel.transaction import Conflict
from fastapi import FastAPI, APIRouter, Request, Response, Depends, Path, Body, Query, Header
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from fast_controller.resource import Resource, get_field_type
from fast_controller.util import docstring_format, InvalidInput, expose_path_params, extract_values


class Action(Enum):
    VIEW = auto()
    SEARCH = auto()
    CREATE = auto()
    UPSERT = auto()
    UPDATE = auto()
    MODIFY = auto()
    RENAME = auto()
    DELETE = auto()


class Controller:
    def __init__(self,
            prefix: Optional[str] = '',
            app: Optional[FastAPI] = None,
            engine: Optional[Engine] = None) -> None:
        self.prefix = prefix
        self.app = None
        self.engine = None
        self.models = None
        if app is not None and engine is not None:
            self.init_app(app, engine)
        self.daos = Depends(self.dao_generator)

    def init_app(self, app: FastAPI, engine: Engine) -> None:
        self.app = app
        self.engine = engine

        @app.exception_handler(InvalidInput)
        async def not_found_handler(request: Request, exc: InvalidInput):
            return JSONResponse(status_code=400, content={"detail": exc.detail})

        @app.exception_handler(NotFound)
        async def not_found_handler(request: Request, exc: NotFound):
            return JSONResponse(status_code=404, content={"detail": exc.detail})

        @app.exception_handler(Conflict)
        async def not_found_handler(request: Request, exc: Conflict):
            return JSONResponse(status_code=409, content={"detail": exc.detail})

    def dao_generator(self) -> DAOFactory:
        """Yields a DAOFactory."""
        with DAOFactory(sessionmaker(bind=self.engine)) as daos:
            yield daos

    @contextmanager
    def dao_context(self):
        yield from self.dao_generator()

    def dependencies_for(self, resource: type[Resource], action: Action) -> list[Depends]:
        return []

    def register_resource(self,
            resource: type[Resource],
            skip: Optional[set[Action]] = None,
            additional_endpoints: Optional[Callable] = None) -> None:
        api_router = APIRouter(
            prefix=self.prefix + resource.get_resource_path(),
            tags=[resource.doc_name()])
        self._register_resource_endpoints(api_router, resource, skip)
        if additional_endpoints:
            additional_endpoints(api_router, self)
        self.app.include_router(api_router)

    def _register_resource_endpoints(self,
            router: APIRouter,
            resource: type[Resource],
            skip: Optional[set[Action]] = None) -> None:
        if skip is None:
            skip = set()
        if Action.SEARCH not in skip:
            self._register_search_endpoint(router, resource)
        if Action.CREATE not in skip:
            self._register_create_endpoint(router, resource)
        if Action.UPSERT not in skip:
            self._register_upsert_endpoint(router, resource)

        pk = [p.name for p in resource.get_pk()]
        path = "/".join([""] + ["{" + p + "}" for p in pk])

        if Action.VIEW not in skip:
            self._register_view_endpoint(router, resource, path, pk)
        if Action.RENAME not in skip:
            self._register_rename_endpoint(router, resource, path, pk)
        if Action.MODIFY not in skip:
            self._register_modify_endpoint(router, resource, path, pk)
        if Action.DELETE not in skip:
            self._register_delete_endpoint(router, resource, path, pk)

    def _register_search_endpoint(self, router: APIRouter, resource: type[Resource]):
        @router.get(
            "/",
            response_model=list[resource.get_output_schema()],
            dependencies=self.dependencies_for(resource, Action.SEARCH))
        @docstring_format(resource=resource.doc_name())
        def search(response: Response,
                   filters: resource.get_search_schema() = Query(),
                   x_page: Optional[int] = Header(default=None, gt=0),
                   x_per_page: Optional[int] = Header(default=None, gt=0),
                   daos: DAOFactory = self.daos) -> list[DAOModel]:
            """Searches for {resource} by criteria"""
            results = daos[resource].find(x_page, x_per_page, **filters.model_dump(exclude_unset=True))
            response.headers["x-total-count"] = str(results.total)
            response.headers["x-page"] = str(results.page)
            response.headers["x-per-page"] = str(results.per_page)
            return results

    def _register_create_endpoint(self, router: APIRouter, resource: type[Resource]):
        @router.post(
            "/",
            response_model=resource.get_detailed_output_schema(),
            status_code=201,
            dependencies=self.dependencies_for(resource, Action.CREATE))
        @docstring_format(resource=resource.doc_name())
        def create(model: resource.get_input_schema(),
                   daos: DAOFactory = self.daos) -> DAOModel:
            """Creates a new {resource}"""
            return daos[resource].create_with(**model.model_dump(exclude_unset=True))

    def _register_upsert_endpoint(self, router: APIRouter, resource: type[Resource]):
        @router.put(
            "/",
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.UPSERT))
        @docstring_format(resource=resource.doc_name())
        def upsert(model: resource.get_input_schema(),
                   daos: DAOFactory = self.daos) -> SQLModel:
            """Creates/modifies a {resource}"""
            daos[resource].upsert(model)
            return model

    def _register_view_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.get(
            path,
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.VIEW))
        @docstring_format(resource=resource.doc_name())
        def view(daos: DAOFactory = self.daos, **kwargs) -> DAOModel:
            """Retrieves a detailed view of a {resource}"""
            return daos[resource].get(*extract_values(kwargs, pk))

        expose_path_params(view, pk)

    def _register_rename_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.post(
            f'{path}/rename',
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.RENAME))
        @docstring_format(resource=resource.doc_name())
        def rename(daos: DAOFactory = self.daos, **kwargs) -> DAOModel:
            """Renames a {resource}"""
            dao = daos[resource]
            current = dao.get(*extract_values(kwargs, pk))

            if len(pk) == 1:
                new_value = kwargs['new_pk']
                dao.rename(current, dao.get(new_value))
            else:
                new_values = kwargs.get('new_pk', {})
                new_pk_values = [new_values.get(field, kwargs[field]) for field in pk]
                dao.rename(current, dao.get(*new_pk_values))

            return current

        expose_path_params(rename, pk)

        sig = inspect.signature(rename)
        new_params = list(sig.parameters.values())
        new_params.append(inspect.Parameter(
            'new_pk',
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=Body(),
            annotation=resource.get_pk_schema() if len(pk) > 1 else get_field_type(next(iter(resource.get_pk())))
        ))

        rename.__signature__ = sig.replace(parameters=new_params)

    def _register_merge_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.post(
            f'{path}/merge',
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.RENAME))
        @docstring_format(resource=resource.doc_name())
        def merge(pk0=Path(alias=pk[0]),
                   target_id=Body(alias=pk[0]),
                   daos: DAOFactory = self.daos) -> DAOModel:
            source = daos[resource].get(pk0)
         #   for model in all_models(self.engine):
        #        for column in model.get_references_of(resource):
                    #daos[type[model]].find(column.name=)
         #           if fk.column.table.name == target_table_name and fk.column.name in target_column_values:
        #                print(f"Foreign key in table {table.name} references the column '{fk.column.name}' in {target_table.name}")
        #                # Retrieve rows in this table that reference the target row
        #                conn = engine.connect()
        #                condition = (table.c[fk.parent.name] == target_column_values[fk.column.name])
        #                result = conn.execute(table.select().where(condition))
       #                 referencing_rows.extend(result.fetchall())
        #                conn.close()
#
        #    return referencing_rows

    def _register_update_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.put(
            path,
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.UPDATE))
        @docstring_format(resource=resource.doc_name())
        def update(model: resource.get_update_schema(),  # TODO - Remove PK from input schema
                   pk0=Path(alias=pk[0]),
                   daos: DAOFactory = self.daos) -> DAOModel:
            """Creates/modifies a {resource}"""
            result = daos[resource].get(pk0)
            result.set_values(**model.model_dump(exclude_unset=False))
            daos[resource].commit(result)
            return result

    def _register_modify_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.patch(
            path,
            response_model=resource.get_detailed_output_schema(),
            dependencies=self.dependencies_for(resource, Action.MODIFY))
        @docstring_format(resource=resource.doc_name())
        def modify(model: resource.get_update_schema(),  # TODO - Remove PK from input schema
                 daos: DAOFactory = self.daos, **kwargs) -> DAOModel:
            """Modifies specific fields of a {resource} while leaving others unchanged"""
            dao = daos[resource]
            result = dao.get(*extract_values(kwargs, pk))
            result.set_values(**model.model_dump(exclude_unset=True))
            dao.commit(result)
            return result

        expose_path_params(modify, pk)

    def _register_delete_endpoint(self,
            router: APIRouter,
            resource: type[Resource],
            path: str,
            pk: list[str]):
        @router.delete(
            path,
            status_code=204,
            dependencies=self.dependencies_for(resource, Action.DELETE))
        @docstring_format(resource=resource.doc_name())
        def delete(daos: DAOFactory = self.daos, **kwargs) -> None:
            """Deletes a {resource}"""
            daos[resource].remove(*extract_values(kwargs, pk))

        expose_path_params(delete, pk)
