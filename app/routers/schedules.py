"""Maintenance schedule routes and the due-soon dashboard (User Story 4).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/schedule_service.py`
and `app/services/notification_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.form_errors import error_context
from app.models.requests import ScheduleRequest
from app.models.schedule_kinds import PERIOD_UNITS, SERVICE_TYPES, UNIT_LABELS, USAGE_UNITS
from app.services import (
    bike_service,
    builder_service,
    component_service,
    notification_service,
    schedule_service,
)
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _parse(form, *, is_active: bool) -> ScheduleRequest:
    """Checkboxes are present in the post only when ticked."""
    return ScheduleRequest(
        service_type=form.get("service_type", ""),
        interval_kind=form.get("interval_kind", ""),
        interval_unit_usage=form.get("interval_unit_usage", ""),
        interval_unit_period=form.get("interval_unit_period", ""),
        interval_value=form.get("interval_value", ""),
        is_recurring=form.get("is_recurring") is not None,
        notify=form.get("notify") is not None,
        is_active=is_active,
    )


def _owner(kind: str, item_id: int):
    return bike_service.get_bike(item_id) if kind == "bike" else component_service.get_component(item_id)


def _owner_page(kind: str, owner_id: int) -> str:
    return f"/{kind}s/{owner_id}/schedules"


def _from_owner(request: Request) -> bool:
    """Only the fixed flag `from=owner` is honored, never a URL (no open redirect)."""
    return request.query_params.get("from") == "owner"


def _after(request: Request, schedule) -> str:
    """Where to go after changing a schedule: its owner's Schedules page, or Maintenance due."""
    if _from_owner(request):
        kind, owner = _schedule_owner(schedule)
        return _owner_page(kind, owner.id)
    return "/maintenance/due"


def _form_context(
    kind: str, owner, schedule, errors=(), field_errors=None, values=None, from_owner: bool = False
) -> dict:
    return {
        "owner": owner,
        "owner_kind": kind,
        "schedule": schedule,
        "errors": list(errors),
        "field_errors": field_errors or {},
        "values": values or {},
        "defaults": schedule_service.form_defaults(schedule),
        "service_types": [{"value": t, "label": t} for t in SERVICE_TYPES],
        "usage_options": [{"value": u, "label": UNIT_LABELS[u]} for u in USAGE_UNITS],
        "period_options": [{"value": u, "label": UNIT_LABELS[u]} for u in PERIOD_UNITS],
        "action": (f"/schedules/{schedule.id}" + ("?from=owner" if from_owner else ""))
        if schedule
        else _owner_page(kind, owner.id),
        # a new schedule is added from the item's Schedules page (056); an existing one is edited
        # from there (`from=owner`) or from the Maintenance due page (specs/031-screen-polish)
        "cancel_url": _owner_page(kind, owner.id) if (from_owner or not schedule) else "/maintenance/due",
    }


def _schedule_owner(schedule):
    kind = "bike" if schedule.bike_id is not None else "component"
    return kind, _owner(kind, schedule.bike_id if kind == "bike" else schedule.component_id)


def _board_context(account, show_all: bool, *, done_id: int | None = None) -> dict:
    """Board data; `done_id` names a just-completed schedule to confirm and highlight."""
    items = schedule_service.list_due_overview(lead_time_days=account.notification_lead_time_days)
    done = next((i for i in items if i.schedule.id == done_id), None) if done_id else None
    return {
        "items": items,
        "board": schedule_service.split_attention(items, show_all=show_all),
        "show_all": show_all,
        "notice": (
            f"Marked done: {done.schedule.name}. {schedule_service.next_due_text(done)}."
            if done
            else None
        ),
        "just_done": done.schedule.id if done else None,
    }


@router.get("/maintenance/due", name="due_dashboard")
def due_dashboard(
    request: Request,
    account=Depends(require_account),
    all_tasks: str | None = Query(default=None, alias="all"),
    done: str | None = Query(default=None),
):
    done_id = int(done) if done and done.isdigit() and len(done) <= 9 else None
    context = _board_context(account, show_all=all_tasks == "1", done_id=done_id)  # "1" = on
    return _render(request, "schedules/due_dashboard.html", context)


@router.post("/notifications/{notification_id}/acknowledge", name="acknowledge_notification")
def acknowledge_notification(
    request: Request, notification_id: int, account=Depends(require_account)
):
    notification_service.acknowledge(notification_id)
    if request.headers.get("hx-request") == "true":
        return HTMLResponse("")  # the dismissed alert is removed in place
    return RedirectResponse(url="/maintenance/due", status_code=303)


def _list_view(request: Request, account, kind: str, item_id: int):
    """The item's Schedules page: add, edit and delete in one place (specs/056)."""
    owner = _owner(kind, item_id)
    if owner is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    trail = builder_service.breadcrumbs(f"{kind}:{item_id}")
    crumbs = [*trail[:-1], (owner.name, f"/{kind}s/{item_id}"), ("Schedules", None)]
    items = schedule_service.list_overview_for_owner(
        kind, item_id, lead_time_days=account.notification_lead_time_days
    )
    rows = [{"item": item, "interval": schedule_service.interval_text(item.schedule)} for item in items]
    return _render(
        request,
        "schedules/owner_list.html",
        {"owner": owner, "owner_kind": kind, "rows": rows, "crumbs": crumbs, "new_url": f"{_owner_page(kind, item_id)}/new"},
    )


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
            _form_context(kind, owner, None, **error_context(form, exc)),
            status_code=422,
        )
    schedule_service.create_schedule(
        **{f"{kind}_id": item_id},
        service_type=payload.service_type,
        interval_kind=payload.interval_kind,
        interval_value=payload.interval_value,
        interval_unit=payload.interval_unit,
        is_recurring=payload.is_recurring,
        notify=payload.notify,
    )
    return RedirectResponse(url=_owner_page(kind, item_id), status_code=303)


@router.get("/bikes/{bike_id}/schedules", name="bike_schedules")
def bike_schedules(request: Request, bike_id: int, account=Depends(require_account)):
    return _list_view(request, account, "bike", bike_id)


@router.get("/components/{component_id}/schedules", name="component_schedules")
def component_schedules(request: Request, component_id: int, account=Depends(require_account)):
    return _list_view(request, account, "component", component_id)


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
    return _render(
        request, "schedules/form.html", _form_context(kind, owner, schedule, [], from_owner=_from_owner(request))
    )


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
            _form_context(kind, owner, schedule, from_owner=_from_owner(request), **error_context(form, exc)),
            status_code=422,
        )
    schedule_service.update_schedule(
        schedule_id,
        service_type=payload.service_type,
        interval_kind=payload.interval_kind,
        interval_value=payload.interval_value,
        interval_unit=payload.interval_unit,
        is_recurring=payload.is_recurring,
        notify=payload.notify,
        is_active=payload.is_active,
    )
    return RedirectResponse(url=_after(request, schedule), status_code=303)


@router.post("/schedules/{schedule_id}/complete", name="complete_schedule")
def complete_schedule(
    request: Request,
    schedule_id: int,
    account=Depends(require_account),
    all_tasks: str | None = Form(default=None, alias="all"),
):
    try:
        schedule_service.complete_schedule(schedule_id)
    except LookupError:
        return PlainTextResponse("Schedule not found", status_code=404)
    if request.headers.get("hx-request") == "true":
        # Re-render the whole board so the completed task moves to its new place and says so.
        context = _board_context(account, show_all=all_tasks == "1", done_id=schedule_id)
        return _render(request, "partials/attention_board.html", context)
    return RedirectResponse(url=f"/maintenance/due?done={schedule_id}", status_code=303)


@router.post("/schedules/{schedule_id}/delete", name="delete_schedule")
def delete_schedule(request: Request, schedule_id: int, account=Depends(require_account)):
    schedule = schedule_service.get_schedule(schedule_id)
    try:
        schedule_service.delete_schedule(schedule_id)
    except LookupError:
        return PlainTextResponse("Schedule not found", status_code=404)
    return RedirectResponse(url=_after(request, schedule), status_code=303)
