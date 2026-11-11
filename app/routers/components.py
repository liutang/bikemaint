"""Component routes: storage list, detail, create/edit/move/delete (User Story 1).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/component_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import (
    COMPONENT_TYPES,
    ComponentCreateRequest,
    ComponentMoveRequest,
    ComponentUpdateRequest,
)
from app.services import component_service
from app.services.auth_dependency import require_account
from app.services.component_service import ComponentNestingConflictError

router = APIRouter()


def _optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _subtree(component) -> list[dict]:
    descendants = component_service.get_descendants(component.id)
    return component_service.build_tree([component], [component, *descendants])[0]["children"]


@router.get("/components", name="components_in_storage")
def components_in_storage(request: Request, account=Depends(require_account)):
    components = component_service.list_in_storage()
    return _render(request, "components/list.html", {"components": components})


@router.get("/components/new", name="new_component_form")
def new_component_form(
    request: Request,
    account=Depends(require_account),
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
):
    return _render(
        request,
        "components/form.html",
        {
            "component": None,
            "component_types": COMPONENT_TYPES,
            "parent_bike_id": parent_bike_id,
            "parent_component_id": parent_component_id,
            "errors": [],
        },
    )


@router.post("/components", name="create_component")
async def create_component(request: Request, account=Depends(require_account)):
    form = await request.form()
    parent_bike_id = _optional_int(form.get("parent_bike_id"))
    parent_component_id = _optional_int(form.get("parent_component_id"))
    try:
        payload = ComponentCreateRequest(
            name=form.get("name", ""),
            component_type=form.get("component_type", ""),
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
            manual_baseline_mileage=_optional_float(form.get("manual_baseline_mileage")),
        )
    except ValidationError as exc:
        return _render(
            request,
            "components/form.html",
            {
                "component": None,
                "component_types": COMPONENT_TYPES,
                "parent_bike_id": parent_bike_id,
                "parent_component_id": parent_component_id,
                "errors": [error["msg"] for error in exc.errors()],
            },
            status_code=422,
        )
    try:
        component = component_service.create_component(**payload.model_dump())
    except ComponentNestingConflictError as exc:
        return _render(
            request,
            "components/form.html",
            {
                "component": None,
                "component_types": COMPONENT_TYPES,
                "parent_bike_id": parent_bike_id,
                "parent_component_id": parent_component_id,
                "errors": [str(exc)],
            },
            status_code=422,
        )
    if request.headers.get("hx-request") == "true":
        return _render(
            request, "components/detail.html", {"component": component, "tree": []}
        )
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.get("/components/{component_id}", name="component_detail")
def component_detail(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    return _render(
        request, "components/detail.html", {"component": component, "tree": _subtree(component)}
    )


@router.get("/components/{component_id}/edit", name="edit_component_form")
def edit_component_form(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    return _render(
        request,
        "components/form.html",
        {
            "component": component,
            "component_types": COMPONENT_TYPES,
            "parent_bike_id": component.parent_bike_id,
            "parent_component_id": component.parent_component_id,
            "errors": [],
        },
    )


@router.post("/components/{component_id}", name="update_component")
async def update_component(request: Request, component_id: int, account=Depends(require_account)):
    form = await request.form()
    existing = component_service.get_component(component_id)
    if existing is None:
        return PlainTextResponse("Component not found", status_code=404)
    try:
        payload = ComponentUpdateRequest(
            name=form.get("name", ""),
            component_type=form.get("component_type", ""),
            manual_baseline_mileage=_optional_float(form.get("manual_baseline_mileage")),
        )
    except ValidationError as exc:
        return _render(
            request,
            "components/form.html",
            {
                "component": existing,
                "component_types": COMPONENT_TYPES,
                "parent_bike_id": existing.parent_bike_id,
                "parent_component_id": existing.parent_component_id,
                "errors": [error["msg"] for error in exc.errors()],
            },
            status_code=422,
        )
    try:
        component = component_service.update_component(component_id, **payload.model_dump())
    except ComponentNestingConflictError as exc:
        return _render(
            request,
            "components/form.html",
            {
                "component": existing,
                "component_types": COMPONENT_TYPES,
                "parent_bike_id": existing.parent_bike_id,
                "parent_component_id": existing.parent_component_id,
                "errors": [str(exc)],
            },
            status_code=422,
        )
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.post("/components/{component_id}/move", name="move_component")
async def move_component(request: Request, component_id: int, account=Depends(require_account)):
    form = await request.form()
    existing = component_service.get_component(component_id)
    if existing is None:
        return PlainTextResponse("Component not found", status_code=404)
    try:
        payload = ComponentMoveRequest(
            parent_bike_id=_optional_int(form.get("parent_bike_id")),
            parent_component_id=_optional_int(form.get("parent_component_id")),
        )
    except ValidationError as exc:
        return _render(
            request,
            "components/detail.html",
            {
                "component": existing,
                "tree": _subtree(existing),
                "errors": [error["msg"] for error in exc.errors()],
            },
            status_code=422,
        )
    try:
        component = component_service.move_component(component_id, **payload.model_dump())
    except (ComponentNestingConflictError, ValueError) as exc:
        return _render(
            request,
            "components/detail.html",
            {"component": existing, "tree": _subtree(existing), "errors": [str(exc)]},
            status_code=422,
        )
    if request.headers.get("hx-request") == "true":
        return _render(
            request, "components/detail.html", {"component": component, "tree": _subtree(component)}
        )
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.post("/components/{component_id}/delete", name="delete_component")
async def delete_component(request: Request, component_id: int, account=Depends(require_account)):
    form = await request.form()
    confirmed = form.get("confirmed") == "true"
    try:
        component_service.delete_component(component_id, confirmed=confirmed)
    except component_service.ConfirmationRequiredError as exc:
        return _render(
            request,
            "partials/confirm_delete.html",
            {
                "item_type": "component",
                "message": str(exc),
                "action": f"/components/{component_id}/delete",
            },
        )
    if request.headers.get("hx-request") == "true":
        components = component_service.list_in_storage()
        return _render(request, "components/list.html", {"components": components})
    return RedirectResponse(url="/components", status_code=303)
