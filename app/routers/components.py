"""Component routes: storage list, detail, create/edit/move/delete (User Story 1).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/component_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.models import component_kinds
from app.models.form_errors import error_context, message_context

from app.models.requests import (
    ComponentCreateRequest,
    ComponentMoveRequest,
    ComponentUpdateRequest,
    MoveTargetRequest,
)
from app.routers.screen import render_screen
from app.services import builder_service, component_service
from app.services.auth_dependency import require_account
from app.services.component_service import ComponentPlacementError

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


def _form_context(component, parent_bike_id, parent_component_id, extra: dict | None = None) -> dict:
    """Context for components/form.html: every offered kind, plus a part's own older kind."""
    types = list(component_kinds.COMPONENT_TYPES)
    if component is not None and component.component_type not in types:
        types = [component.component_type, *types]  # an older kind stays selectable on its own part
    types = [{"value": t, "label": component_kinds.kind_name(t)} for t in types]
    if component is None:
        crumbs = [("Garage", "/"), ("Storage", "/components"), ("Add a part", None)]
    else:
        trail = builder_service.breadcrumbs(f"component:{component.id}")
        crumbs = [*trail[:-1], (component.name, f"/components/{component.id}"), ("Edit", None)]
    return {
        "crumbs": crumbs,
        "component": component,
        "component_types": types,
        "parent_bike_id": parent_bike_id,
        "parent_component_id": parent_component_id,
        "errors": [],
        **(extra or {}),
    }


def _message(exc: Exception) -> str:
    return "That place no longer exists." if isinstance(exc, LookupError) else str(exc)


@router.get("/components", name="components_in_storage")
def components_in_storage(request: Request, account=Depends(require_account)):
    return _render(
        request,
        "components/list.html",
        {
            "components": component_service.list_in_storage(),
            "crumbs": [("Garage", "/"), ("Storage", None)],
        },
    )


@router.get("/components/new", name="new_component_form")
def new_component_form(request: Request, account=Depends(require_account)):
    """Add a part to storage; mounting it on a bike is done on the bike's screen."""
    return _render(request, "components/form.html", _form_context(None, None, None))


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
            _form_context(None, parent_bike_id, parent_component_id, error_context(form, exc)),
            status_code=422,
        )
    try:
        component = component_service.create_component(**payload.model_dump())
    except (ComponentPlacementError, LookupError) as exc:
        return _render(
            request,
            "components/form.html",
            _form_context(
                None, parent_bike_id, parent_component_id, message_context(form, _message(exc))
            ),
            status_code=422,
        )
    if request.headers.get("hx-request") == "true":
        return _render(
            request, "components/detail.html", {"component": component, "tree": []}
        )
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.get("/components/{component_id}", name="component_detail")
def component_detail(request: Request, component_id: int, account=Depends(require_account)):
    return render_screen(request, f"component:{component_id}")


@router.get("/components/{component_id}/edit", name="edit_component_form")
def edit_component_form(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    return _render(
        request,
        "components/form.html",
        _form_context(component, component.parent_bike_id, component.parent_component_id),
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
            _form_context(
                existing, existing.parent_bike_id, existing.parent_component_id, error_context(form, exc)
            ),
            status_code=422,
        )
    try:
        component = component_service.update_component(component_id, **payload.model_dump())
    except ComponentPlacementError as exc:
        return _render(
            request,
            "components/form.html",
            _form_context(
                existing,
                existing.parent_bike_id,
                existing.parent_component_id,
                message_context(form, str(exc)),
            ),
            status_code=422,
        )
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.post("/components/{component_id}/move", name="move_component")
async def move_component(request: Request, component_id: int, account=Depends(require_account)):
    """Kept for compatibility (and plain forms); the unified screen uses `/builder/move`."""
    form = await request.form()
    existing = component_service.get_component(component_id)
    if existing is None:
        return PlainTextResponse("Component not found", status_code=404)
    root = f"component:{component_id}"
    try:
        if "target" in form:  # the "Move to..." select
            parents = MoveTargetRequest(target=form.get("target", "")).parents()
        else:  # legacy: explicit parent id fields
            parents = ComponentMoveRequest(
                parent_bike_id=_optional_int(form.get("parent_bike_id")),
                parent_component_id=_optional_int(form.get("parent_component_id")),
            ).model_dump()
    except ValidationError as exc:
        return render_screen(
            request, root, message="; ".join(e["msg"] for e in exc.errors()), status_code=422
        )
    try:
        component = component_service.move_component(component_id, **parents)
    except (ComponentPlacementError, ValueError, LookupError) as exc:
        return render_screen(request, root, message=_message(exc), status_code=422)
    if request.headers.get("hx-request") == "true":
        return render_screen(request, f"component:{component.id}")
    return RedirectResponse(url=f"/components/{component.id}", status_code=303)


@router.post("/components/{component_id}/delete", name="delete_component")
async def delete_component(request: Request, component_id: int, account=Depends(require_account)):
    """Delete a part. Always asks first, with a Keep install history choice (specs/030)."""
    form = await request.form()
    htmx = request.headers.get("hx-request") == "true"
    try:
        if form.get("confirmed") != "true":
            message = component_service.delete_consequences(component_id)
            context = {
                "item_type": "part",
                "message": message,
                "action": f"/components/{component_id}/delete",
                "cancel_url": f"/components/{component_id}",
                "offer_keep_history": True,
            }
            template = "partials/confirm_delete.html" if htmx else "confirm_delete_page.html"
            return _render(request, template, context)
        component_service.delete_component(
            component_id, confirmed=True, keep_history=form.get("keep_history") is not None
        )
    except LookupError:
        return PlainTextResponse("Part not found", status_code=404)
    if htmx:
        return Response(status_code=200, headers={"HX-Redirect": "/components"})
    return RedirectResponse(url="/components", status_code=303)
