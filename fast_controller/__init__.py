from contextlib import contextmanager
from enum import Enum, auto
from typing import Optional, Callable
import inspect

from daomodel import DAOModel
from daomodel.dao import NotFound
from daomodel.db import DAOFactory
from daomodel.transaction import Conflict
from fastapi import FastAPI, APIRouter, Request, Response, Depends, Path, Body, Query, Header
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from fast_controller.resource import Resource, get_field_type
from fast_controller.util import docstring_format, InvalidInput, expose_path_params, extract_values, inflect


class Action(Enum):
    SEARCH = auto()
    CREATE = auto()
    UPSERT = auto()
    VIEW = auto()
    UPDATE = auto()
    MODIFY = auto()
    DELETE = auto()
    RENAME = auto()

    def register_endpoint(self, controller, router: APIRouter, resource: type[Resource]):
        {
            Action.SEARCH: _register_search_endpoint,
            Action.CREATE: _register_create_endpoint,
            Action.UPSERT: _register_upsert_endpoint,
            Action.VIEW: _register_view_endpoint,
            Action.UPDATE: _register_update_endpoint,
            Action.MODIFY: _register_modify_endpoint,
            Action.DELETE: _register_delete_endpoint,
            Action.RENAME: _register_rename_endpoint,
        }[self](controller, router, resource)


def _construct_path(pk):
    path = '/'.join([''] + ['{' + p + '}' for p in pk])
    return path


def _register_search_endpoint(controller, router: APIRouter, resource: type[Resource]):
    @router.get('/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url='', status_code=307)

    @router.get(
        '',
        response_model=list[resource.get_output_schema()],
        dependencies=controller.dependencies_for(resource, Action.SEARCH))
    @docstring_format(resource=resource.resource_name())
    def search(response: Response,
               filters: resource.get_search_schema() = Query(),
               x_page: Optional[int] = Header(default=None, gt=0),
               x_per_page: Optional[int] = Header(default=None, gt=0),
               x_order: Optional[str] = Header(default=None),
               x_duplicate: Optional[str] = Header(default=None),  # TODO: move to filters
               x_unique: Optional[str] = Header(default=None),  # TODO: move to filters
               daos: DAOFactory = controller.daos) -> list[DAOModel]:
        """Searches for {resource} by criteria"""
        provided_filters = filters.model_dump(exclude_unset=True)
        results = daos[resource].find(x_page, x_per_page, x_order, x_duplicate, x_unique, **provided_filters)
        response.headers["x-total-count"] = str(results.total)
        response.headers["x-page"] = str(results.page)
        response.headers["x-per-page"] = str(results.per_page)
        return results


def _register_create_endpoint(controller, router: APIRouter, resource: type[Resource]):
    @router.post('/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url='', status_code=307)

    @router.post(
        '',
        response_model=resource.get_detailed_output_schema(),
        status_code=201,
        dependencies=controller.dependencies_for(resource, Action.CREATE))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def create(model: resource.get_input_schema(),
               daos: DAOFactory = controller.daos) -> DAOModel:
        """Creates {resource}"""
        return daos[resource].create_with(**model.model_dump(exclude_unset=True))


def _register_upsert_endpoint(controller, router: APIRouter, resource: type[Resource]):
    @router.put('/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url='', status_code=307)

    @router.put(
        '',
        response_model=resource.get_detailed_output_schema(),
        dependencies=controller.dependencies_for(resource, Action.UPSERT))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def upsert(model: resource.get_input_schema(),
               daos: DAOFactory = controller.daos) -> SQLModel:
        """Creates/modifies {resource}"""
        daos[resource].upsert(model)
        return model


def _register_view_endpoint(controller, router: APIRouter, resource: type[Resource]):
    pk = [p.name for p in resource.get_pk()]
    path = _construct_path(pk)

    @router.get(f'{path}/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url=path, status_code=307)

    @router.get(
        path,
        response_model=resource.get_detailed_output_schema(),
        dependencies=controller.dependencies_for(resource, Action.VIEW))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def view(daos: DAOFactory = controller.daos, **kwargs) -> DAOModel:
        """Retrieves a detailed view of {resource}"""
        return daos[resource].get(*extract_values(kwargs, pk))

    expose_path_params(view, pk)


def _register_update_endpoint(controller, router: APIRouter, resource: type[Resource]):
    pk = [p.name for p in resource.get_pk()]
    path = _construct_path(pk)

    @router.put(f'{path}/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url=path, status_code=307)

    @router.put(
        path,
        response_model=resource.get_detailed_output_schema(),
        dependencies=controller.dependencies_for(resource, Action.UPDATE))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def update(model: resource.get_update_schema(),  # TODO - Remove PK from input schema
               pk0=Path(alias=pk[0]),
               daos: DAOFactory = controller.daos) -> DAOModel:
        """Modifies {resource}"""
        result = daos[resource].get(pk0)
        result.set_values(**model.model_dump(exclude_unset=False))
        daos[resource].commit(result)
        return result

    expose_path_params(update, pk)


def _register_modify_endpoint(controller, router: APIRouter, resource: type[Resource]):
    pk = [p.name for p in resource.get_pk()]
    path = _construct_path(pk)

    @router.patch(f'{path}/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url=path, status_code=307)

    @router.patch(
        path,
        response_model=resource.get_detailed_output_schema(),
        dependencies=controller.dependencies_for(resource, Action.MODIFY))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def modify(model: resource.get_update_schema(),  # TODO - Remove PK from input schema
               daos: DAOFactory = controller.daos, **kwargs) -> DAOModel:
        """Modifies specific fields of {resource} while leaving others unchanged"""
        dao = daos[resource]
        result = dao.get(*extract_values(kwargs, pk))
        result.set_values(**model.model_dump(exclude_unset=True))
        dao.commit(result)
        return result

    expose_path_params(modify, pk)


def _register_delete_endpoint(controller, router: APIRouter, resource: type[Resource]):
    pk = [p.name for p in resource.get_pk()]
    path = _construct_path(pk)

    @router.delete(f'{path}/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url=path, status_code=307)

    @router.delete(
        path,
        status_code=204,
        dependencies=controller.dependencies_for(resource, Action.DELETE))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def delete(daos: DAOFactory = controller.daos, **kwargs) -> None:
        """Deletes {resource}"""
        daos[resource].remove(*extract_values(kwargs, pk))

    expose_path_params(delete, pk)


def _register_rename_endpoint(controller, router: APIRouter, resource: type[Resource]):
    pk = [p.name for p in resource.get_pk()]
    path = f'{_construct_path(pk)}/rename'

    @router.post(f'{path}/', include_in_schema=False)
    async def redirect():
        return RedirectResponse(url=path, status_code=307)

    @router.post(
        path,
        response_model=resource.get_detailed_output_schema(),
        dependencies=controller.dependencies_for(resource, Action.RENAME))
    @docstring_format(resource=inflect.a(resource.doc_name()))
    def rename(daos: DAOFactory = controller.daos, **kwargs) -> DAOModel:
        """Renames {resource}"""
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


class Controller:
    def __init__(self,
                 prefix: Optional[str] = '',
                 app: Optional[FastAPI] = None,
                 engine: Optional[Engine] = None) -> None:
        self.prefix = prefix
        self.app = None
        self.engine = None
        self.models = None
        self.daos = Depends(self.dao_generator)
        if app is not None and engine is not None:
            self.init_app(app, engine)

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

    def get_path_for(self, resource: type[Resource]) -> str:
        return self.prefix + resource.get_resource_path()

    def register_resource(self,
            resource: type[Resource],
            skip: Optional[set[Action]] = frozenset(),
            additional_endpoints: Optional[Callable] = None) -> None:
        api_router = APIRouter(
            prefix=self.get_path_for(resource),
            tags=[resource.resource_name()])
        self._register_resource_endpoints(api_router, resource, skip)
        if additional_endpoints:
            additional_endpoints(api_router, self)
        self.app.include_router(api_router)

    def _register_resource_endpoints(self,
            router: APIRouter,
            resource: type[Resource],
            skip: Optional[set[Action]] = frozenset()) -> None:
        for action in Action:
            if action not in skip:
                action.register_endpoint(self, router, resource)

    # TODO: finish implementing merge endpoint
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
