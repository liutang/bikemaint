"""Maintenance log routes for bikes and components (User Story 3).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/maintenance_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import MaintenanceLogRequest
from app.services import bike_service, component_service, maintenance_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return -1.0  # fails the request schema's ge=0 check with a validation message


def _parse(form) -> MaintenanceLogRequest:
    return MaintenanceLogRequest(
        description=form.get("description", ""),
        performed_at=form.get("performed_at", ""),
        mileage_at_service=_optional_float(form.get("mileage_at_service")),
    )


def _owner(kind: str, item_id: int):
    return bike_service.get_bike(item_id) if kind == "bike" else component_service.get_component(item_id)


def _history_url(kind: str, item_id: int) -> str:
    return f"/{kind}s/{item_id}/maintenance"


def _history(kind: str, item_id: int):
    if kind == "bike":
        return maintenance_service.list_for_bike(item_id)
    return maintenance_service.list_for_component(item_id)


def _form_context(kind: str, item, entry, errors: list[str]) -> dict:
    return {
        "item": item,
        "item_kind": kind,
        "entry": entry,
        "errors": errors,
        "action": (
            f"/maintenance/{entry.id}" if entry else _history_url(kind, item.id)
        ),
    }


def _list_view(request: Request, kind: str, item_id: int):
    item = _owner(kind, item_id)
    if item is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    return _render(
        request,
        "maintenance/history_list.html",
        {"item": item, "item_kind": kind, "entries": _history(kind, item_id)},
    )


def _new_view(request: Request, kind: str, item_id: int):
    item = _owner(kind, item_id)
    if item is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    return _render(request, "maintenance/form.html", _form_context(kind, item, None, []))


async def _create(request: Request, kind: str, item_id: int):
    item = _owner(kind, item_id)
    if item is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    form = await request.form()
    try:
        payload = _parse(form)
    except ValidationError as exc:
        return _render(
            request,
            "maintenance/form.html",
            _form_context(kind, item, None, [e["msg"] for e in exc.errors()]),
            status_code=422,
        )
    maintenance_service.log_maintenance(
        **{f"{kind}_id": item_id},
        description=payload.description,
        performed_at=payload.performed_at.isoformat(),
        mileage_at_service=payload.mileage_at_service,
    )
    return RedirectResponse(url=_history_url(kind, item_id), status_code=303)


@router.get("/bikes/{bike_id}/maintenance", name="bike_maintenance_history")
def bike_maintenance_history(request: Request, bike_id: int, account=Depends(require_account)):
    return _list_view(request, "bike", bike_id)


@router.get("/bikes/{bike_id}/maintenance/new", name="new_bike_maintenance_form")
def new_bike_maintenance_form(request: Request, bike_id: int, account=Depends(require_account)):
    return _new_view(request, "bike", bike_id)


@router.post("/bikes/{bike_id}/maintenance", name="create_bike_maintenance")
async def create_bike_maintenance(request: Request, bike_id: int, account=Depends(require_account)):
    return await _create(request, "bike", bike_id)


@router.get("/components/{component_id}/maintenance", name="component_maintenance_history")
def component_maintenance_history(
    request: Request, component_id: int, account=Depends(require_account)
):
    return _list_view(request, "component", component_id)


@router.get("/components/{component_id}/maintenance/new", name="new_component_maintenance_form")
def new_component_maintenance_form(
    request: Request, component_id: int, account=Depends(require_account)
):
    return _new_view(request, "component", component_id)


@router.post("/components/{component_id}/maintenance", name="create_component_maintenance")
async def create_component_maintenance(
    request: Request, component_id: int, account=Depends(require_account)
):
    return await _create(request, "component", component_id)


def _entry_owner(entry):
    kind = "bike" if entry.bike_id is not None else "component"
    item_id = entry.bike_id if entry.bike_id is not None else entry.component_id
    return kind, item_id


@router.get("/maintenance/{entry_id}/edit", name="edit_maintenance_form")
def edit_maintenance_form(request: Request, entry_id: int, account=Depends(require_account)):
    entry = maintenance_service.get_entry(entry_id)
    if entry is None:
        return PlainTextResponse("Maintenance entry not found", status_code=404)
    kind, item_id = _entry_owner(entry)
    return _render(
        request, "maintenance/form.html", _form_context(kind, _owner(kind, item_id), entry, [])
    )


@router.post("/maintenance/{entry_id}", name="update_maintenance")
async def update_maintenance(request: Request, entry_id: int, account=Depends(require_account)):
    entry = maintenance_service.get_entry(entry_id)
    if entry is None:
        return PlainTextResponse("Maintenance entry not found", status_code=404)
    kind, item_id = _entry_owner(entry)
    form = await request.form()
    try:
        payload = _parse(form)
    except ValidationError as exc:
        return _render(
            request,
            "maintenance/form.html",
            _form_context(kind, _owner(kind, item_id), entry, [e["msg"] for e in exc.errors()]),
            status_code=422,
        )
    maintenance_service.update_entry(
        entry_id,
        description=payload.description,
        performed_at=payload.performed_at.isoformat(),
        mileage_at_service=(
            entry.mileage_at_service
            if payload.mileage_at_service is None
            else payload.mileage_at_service
        ),
    )
    return RedirectResponse(url=_history_url(kind, item_id), status_code=303)


@router.post("/maintenance/{entry_id}/delete", name="delete_maintenance")
def delete_maintenance(request: Request, entry_id: int, account=Depends(require_account)):
    entry = maintenance_service.get_entry(entry_id)
    if entry is None:
        return PlainTextResponse("Maintenance entry not found", status_code=404)
    kind, item_id = _entry_owner(entry)
    maintenance_service.delete_entry(entry_id)
    return RedirectResponse(url=_history_url(kind, item_id), status_code=303)
