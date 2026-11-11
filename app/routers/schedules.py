"""Maintenance schedule routes and the due-soon dashboard (User Story 4).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/schedule_service.py`
and `app/services/notification_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import ScheduleRequest
from app.services import (
    bike_service,
    component_service,
    notification_service,
    schedule_service,
)
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _blank_to_none(value: str | None) -> str | None:
    return None if value is None or value.strip() == "" else value


def _parse(form, *, is_active: bool) -> ScheduleRequest:
    return ScheduleRequest(
        name=form.get("name", ""),
        interval_miles=_blank_to_none(form.get("interval_miles")),
        interval_days=_blank_to_none(form.get("interval_days")),
        is_active=is_active,
    )


def _owner(kind: str, item_id: int):
    return bike_service.get_bike(item_id) if kind == "bike" else component_service.get_component(item_id)


def _form_context(kind: str, owner, schedule, errors: list[str]) -> dict:
    return {
        "owner": owner,
        "owner_kind": kind,
        "schedule": schedule,
        "errors": errors,
        "action": f"/schedules/{schedule.id}" if schedule else f"/{kind}s/{owner.id}/schedules",
    }


def _schedule_owner(schedule):
    kind = "bike" if schedule.bike_id is not None else "component"
    return kind, _owner(kind, schedule.bike_id if kind == "bike" else schedule.component_id)


@router.get("/maintenance/due", name="due_dashboard")
def due_dashboard(request: Request, account=Depends(require_account)):
    return _render(
        request,
        "schedules/due_dashboard.html",
        {
            "items": schedule_service.list_due_overview(),
            "notifications": notification_service.list_unacknowledged(),
        },
    )


@router.post("/notifications/{notification_id}/acknowledge", name="acknowledge_notification")
def acknowledge_notification(
    request: Request, notification_id: int, account=Depends(require_account)
):
    notification_service.acknowledge(notification_id)
    return RedirectResponse(url="/maintenance/due", status_code=303)


def _new_view(request: Request, kind: str, item_id: int):
    owner = _owner(kind, item_id)
    if owner is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    return _render(request, "schedules/form.html", _form_context(kind, owner, None, []))


async def _create(request: Request, kind: str, item_id: int):
    owner = _owner(kind, item_id)
    if owner is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    form = await request.form()
    try:
        payload = _parse(form, is_active=True)
    except ValidationError as exc:
        return _render(
            request,
            "schedules/form.html",
            _form_context(kind, owner, None, [e["msg"] for e in exc.errors()]),
            status_code=422,
        )
    schedule_service.create_schedule(
        **{f"{kind}_id": item_id},
        name=payload.name,
        interval_miles=payload.interval_miles,
        interval_days=payload.interval_days,
    )
    return RedirectResponse(url="/maintenance/due", status_code=303)


@router.get("/bikes/{bike_id}/schedules/new", name="new_bike_schedule_form")
def new_bike_schedule_form(request: Request, bike_id: int, account=Depends(require_account)):
    return _new_view(request, "bike", bike_id)


@router.post("/bikes/{bike_id}/schedules", name="create_bike_schedule")
async def create_bike_schedule(request: Request, bike_id: int, account=Depends(require_account)):
    return await _create(request, "bike", bike_id)


@router.get("/components/{component_id}/schedules/new", name="new_component_schedule_form")
def new_component_schedule_form(
    request: Request, component_id: int, account=Depends(require_account)
):
    return _new_view(request, "component", component_id)


@router.post("/components/{component_id}/schedules", name="create_component_schedule")
async def create_component_schedule(
    request: Request, component_id: int, account=Depends(require_account)
):
    return await _create(request, "component", component_id)


@router.get("/schedules/{schedule_id}/edit", name="edit_schedule_form")
def edit_schedule_form(request: Request, schedule_id: int, account=Depends(require_account)):
    schedule = schedule_service.get_schedule(schedule_id)
    if schedule is None:
        return PlainTextResponse("Schedule not found", status_code=404)
    kind, owner = _schedule_owner(schedule)
    return _render(request, "schedules/form.html", _form_context(kind, owner, schedule, []))


@router.post("/schedules/{schedule_id}", name="update_schedule")
async def update_schedule(request: Request, schedule_id: int, account=Depends(require_account)):
    schedule = schedule_service.get_schedule(schedule_id)
    if schedule is None:
        return PlainTextResponse("Schedule not found", status_code=404)
    form = await request.form()
    try:
        payload = _parse(form, is_active=form.get("is_active") == "on")
    except ValidationError as exc:
        kind, owner = _schedule_owner(schedule)
        return _render(
            request,
            "schedules/form.html",
            _form_context(kind, owner, schedule, [e["msg"] for e in exc.errors()]),
            status_code=422,
        )
    schedule_service.update_schedule(schedule_id, **payload.model_dump())
    return RedirectResponse(url="/maintenance/due", status_code=303)


@router.post("/schedules/{schedule_id}/complete", name="complete_schedule")
def complete_schedule(request: Request, schedule_id: int, account=Depends(require_account)):
    try:
        schedule_service.complete_schedule(schedule_id)
    except LookupError:
        return PlainTextResponse("Schedule not found", status_code=404)
    if request.headers.get("hx-request") == "true":
        item = schedule_service.get_due_item(schedule_id)
        return _render(request, "partials/due_soon_row.html", {"item": item})
    return RedirectResponse(url="/maintenance/due", status_code=303)


@router.post("/schedules/{schedule_id}/delete", name="delete_schedule")
def delete_schedule(request: Request, schedule_id: int, account=Depends(require_account)):
    try:
        schedule_service.delete_schedule(schedule_id)
    except LookupError:
        return PlainTextResponse("Schedule not found", status_code=404)
    return RedirectResponse(url="/maintenance/due", status_code=303)
