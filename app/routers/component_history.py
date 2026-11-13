"""Install history of a part: log, edit and delete past installation periods (specs/015).

Per Constitution Principle II, this module holds no business logic or direct DB queries — it
translates HTTP concerns to/from `app/services/component_history_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.form_errors import error_context, message_context
from app.models.requests import InstallPeriodRequest
from app.services import bike_service, builder_service, component_history_service as history
from app.models.component_kinds import kind_name
from app.services import component_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    return request.app.state.templates.TemplateResponse(
        request, template, context, status_code=status_code
    )


def _list_url(component_id: int) -> str:
    return f"/components/{component_id}/install-history"


def _crumbs(component, last: str) -> list[tuple[str, str | None]]:
    trail = builder_service.breadcrumbs(f"component:{component.id}")
    return [*trail[:-1], (component.name, f"/components/{component.id}"), (last, None)]


def _from_bike(request: Request):
    """The bike named by `?from_bike=`, if it is a positive integer for an existing bike, else None.

    Editing from a bike's Install History returns there; anything else falls back to the part's page.
    """
    raw = request.query_params.get("from_bike", "")
    if not raw.isdigit() or int(raw) < 1:
        return None
    return bike_service.get_bike(int(raw))


def _bike_history_url(bike) -> str:
    return f"/bikes/{bike.id}/install-history"


def _form_context(component, period, extra: dict | None = None, from_bike=None) -> dict:
    suffix = f"?from_bike={from_bike.id}" if from_bike else ""
    base = f"/install-periods/{period.id}" if period else _list_url(component.id)
    return {
        "component": component,
        "period": period,
        "bike_options": [{"value": str(b.id), "label": b.name} for b in bike_service.list_bikes()],
        "crumbs": _crumbs(component, "Edit period" if period else "Log a period"),
        "action": base + suffix,
        "back_url": _bike_history_url(from_bike) if from_bike else _list_url(component.id),
        "errors": [],
        **(extra or {}),
    }


def _parse(form) -> tuple[InstallPeriodRequest, str, str | None]:
    payload = InstallPeriodRequest(
        bike_id=form.get("bike_id", ""),
        parent_component_id=form.get("parent_component_id", ""),
        installed_date=form.get("installed_date", ""),
        installed_time=form.get("installed_time", ""),
        removed_date=form.get("removed_date", ""),
        removed_time=form.get("removed_time", ""),
    )
    installed = history.moment(payload.installed_date, payload.installed_time)
    removed = (
        history.moment(payload.removed_date, payload.removed_time) if payload.removed_date else None
    )
    return payload, installed, removed


def _problem(exc: Exception) -> tuple[str, str | None]:
    """Message and the field to flag for a failed save."""
    if isinstance(exc, LookupError):
        return "Choose a bike from the list.", "bike_id"
    text = str(exc)
    if "removal" in text.lower():
        return text, "removed_date"
    return text, "installed_date"


@router.get("/components/{component_id}/install-history", name="component_install_history")
def install_history(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Part not found", status_code=404)
    return _render(
        request,
        "components/install_history.html",
        {
            "component": component,
            "rows": history.describe_history(component_id),
            "crumbs": _crumbs(component, "Install history"),
        },
    )


@router.get("/components/{component_id}/install-history/new", name="new_install_period_form")
def new_period_form(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Part not found", status_code=404)
    return _render(request, "components/install_period_form.html", _form_context(component, None))


@router.post("/components/{component_id}/install-history", name="create_install_period")
async def create_period(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Part not found", status_code=404)
    form = await request.form()
    try:
        payload, installed, removed = _parse(form)
        history.log_period(
            component_id, bike_id=payload.bike_id, parent_component_id=payload.parent_component_id,
            installed_at=installed, removed_at=removed,
        )
    except ValidationError as exc:
        extra = error_context(form, exc)
    except (ValueError, LookupError) as exc:
        message, field = _problem(exc)
        extra = message_context(form, message, field=field)
    else:
        return RedirectResponse(url=_list_url(component_id), status_code=303)
    return _render(
        request, "components/install_period_form.html", _form_context(component, None, extra),
        status_code=422,
    )


def _period_and_part(period_id: int):
    period = history.get_period(period_id)
    component = component_service.get_component(period.component_id) if period else None
    return period, component


@router.get("/install-periods/{period_id}/edit", name="edit_install_period_form")
def edit_period_form(request: Request, period_id: int, account=Depends(require_account)):
    period, component = _period_and_part(period_id)
    if period is None or component is None:
        return PlainTextResponse("Period not found", status_code=404)
    return _render(
        request, "components/install_period_form.html",
        _form_context(component, period, from_bike=_from_bike(request)),
    )


@router.post("/install-periods/{period_id}", name="update_install_period")
async def update_period(request: Request, period_id: int, account=Depends(require_account)):
    period, component = _period_and_part(period_id)
    if period is None or component is None:
        return PlainTextResponse("Period not found", status_code=404)
    form = await request.form()
    try:
        payload, installed, removed = _parse(form)
        history.update_period(
            period_id, bike_id=payload.bike_id, parent_component_id=payload.parent_component_id,
            installed_at=installed, removed_at=removed,
        )
    except ValidationError as exc:
        extra = error_context(form, exc)
    except (ValueError, LookupError) as exc:
        message, field = _problem(exc)
        extra = message_context(form, message, field=field)
    else:
        origin = _from_bike(request)
        return RedirectResponse(
            url=_bike_history_url(origin) if origin else _list_url(component.id), status_code=303
        )
    return _render(
        request, "components/install_period_form.html",
        _form_context(component, period, extra, from_bike=_from_bike(request)),
        status_code=422,
    )


@router.post("/install-periods/{period_id}/delete", name="delete_install_period")
def delete_period(request: Request, period_id: int, account=Depends(require_account)):
    period, component = _period_and_part(period_id)
    if period is None or component is None:
        return PlainTextResponse("Period not found", status_code=404)
    try:
        history.delete_period(period_id)
    except ValueError as exc:
        return PlainTextResponse(str(exc), status_code=422)
    origin = _from_bike(request)
    return RedirectResponse(
        url=_bike_history_url(origin) if origin else _list_url(component.id), status_code=303
    )


@router.get("/bikes/{bike_id}/install-history", name="bike_install_history")
def bike_install_history(request: Request, bike_id: int, account=Depends(require_account)):
    """Every part that has been on the bike, with log, edit and delete (specs/022-install-history-split)."""
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(
        request,
        "bikes/install_history.html",
        {
            "bike": bike,
            "rows": history.describe_bike_history(bike_id),
            "crumbs": [("Garage", "/"), (bike.name, f"/bikes/{bike.id}"), ("Install history", None)],
        },
    )


def _bike_form_context(bike, extra: dict | None = None) -> dict:
    parts = [
        {"value": str(c.id), "label": f"{c.name} ({kind_name(c.component_type)})"}
        for c in component_service.list_all_parts()
    ]
    return {
        "bike": bike,
        "part_options": [{"value": "", "label": "Choose a part…"}, *parts],
        "inside_options": [{"value": "", "label": "The bike itself (not inside a part)"}, *parts],
        "crumbs": [
            ("Garage", "/"), (bike.name, f"/bikes/{bike.id}"),
            ("Install history", _bike_history_url(bike)), ("Log a period", None),
        ],
        "errors": [],
        **(extra or {}),
    }


@router.get("/bikes/{bike_id}/install-history/new", name="new_bike_install_period_form")
def new_bike_period_form(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(request, "bikes/install_period_form.html", _bike_form_context(bike))


@router.post("/bikes/{bike_id}/install-history", name="create_bike_install_period")
async def create_bike_period(request: Request, bike_id: int, account=Depends(require_account)):
    """Log a past period of a chosen part on this bike (retroactive entry of old data)."""
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    raw_part = str(form.get("component_id", "")).strip()
    extra = None
    if not raw_part.isdigit() or int(raw_part) < 1:
        extra = message_context(form, "Choose a part from the list.", field="component_id")
    else:
        try:
            payload, installed, removed = _parse({**dict(form), "bike_id": str(bike.id)})
            history.log_period(
                int(raw_part), bike_id=bike.id, parent_component_id=payload.parent_component_id,
                installed_at=installed, removed_at=removed,
            )
        except ValidationError as exc:
            extra = error_context(form, exc)
        except LookupError:
            extra = message_context(form, "Choose a part from the list.", field="component_id")
        except ValueError as exc:
            message, field = _problem(exc)
            extra = message_context(form, message, field=field)
    if extra is None:
        return RedirectResponse(url=_bike_history_url(bike), status_code=303)
    return _render(
        request, "bikes/install_period_form.html", _bike_form_context(bike, extra), status_code=422
    )
