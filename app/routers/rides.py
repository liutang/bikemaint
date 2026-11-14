"""Ride log routes: a bike's rides with full CRUD, and a part's read-only rides.

Per Constitution Principle II, this module holds no business logic or direct DB queries — it
translates HTTP concerns to/from `app/services/ride_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.form_errors import error_context, message_context
from app.models.requests import RideRequest
from app.services import bike_service, builder_service, component_service, ride_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _optional_float(value: str | None) -> float | str:
    """Blank or non-numeric input is passed through so validation reports it beside the field."""
    return "" if value is None else value


def _parse(form) -> RideRequest:
    return RideRequest(
        ride_date=form.get("ride_date", ""),
        ride_time=form.get("ride_time", ""),
        miles=_optional_float(form.get("miles")),
        note=form.get("note", ""),
        bike_id=form.get("bike_id", ""),
        moving_time=form.get("moving_time", ""),
    )


def _bike_crumbs(bike, last: str) -> list[tuple[str, str | None]]:
    return [("Garage", "/"), (bike.name, f"/bikes/{bike.id}"), (last, None)]


def _form_context(bike, ride, extra: dict | None = None) -> dict:
    """Context for rides/form.html (`ride` is None when adding)."""
    return {
        "bike": bike,
        "ride": ride,
        "bike_options": [
            {"value": str(b.id), "label": b.name} for b in (bike_service.list_bikes() if ride else [])
        ],
        "crumbs": _bike_crumbs(bike, "Edit ride" if ride else "Add a ride"),
        "action": f"/rides/{ride.id}" if ride else f"/bikes/{bike.id}/rides",
        "errors": [],
        **(extra or {}),
    }


@router.get("/bikes/{bike_id}/rides", name="bike_rides")
def bike_rides(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(
        request,
        "rides/log.html",
        {"log": ride_service.get_log_for_bike(bike_id), "bike": bike, "crumbs": _bike_crumbs(bike, "Rides")},
    )


@router.get("/bikes/{bike_id}/rides/new", name="new_ride_form")
def new_ride_form(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(request, "rides/form.html", _form_context(bike, None))


@router.post("/bikes/{bike_id}/rides", name="create_ride")
async def create_ride(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    try:
        payload = _parse(form)
        ride_service.create_ride(
            bike_id, day=payload.ride_date, time=payload.ride_time, miles=payload.miles, note=payload.note,
            moving_seconds=ride_service.parse_duration(payload.moving_time),
        )
    except ValidationError as exc:
        return _render(request, "rides/form.html", _form_context(bike, None, error_context(form, exc)), status_code=422)
    except ValueError as exc:
        return _render(
            request, "rides/form.html", _form_context(bike, None, message_context(form, str(exc), field="miles")),
            status_code=422,
        )
    return RedirectResponse(url=f"/bikes/{bike_id}/rides", status_code=303)


@router.get("/rides/{ride_id}/edit", name="edit_ride_form")
def edit_ride_form(request: Request, ride_id: int, account=Depends(require_account)):
    ride = ride_service.get_ride(ride_id)
    bike = bike_service.get_bike(ride.bike_id) if ride and ride.bike_id else None
    if ride is None or bike is None:
        return PlainTextResponse("Ride not found", status_code=404)
    return _render(request, "rides/form.html", _form_context(bike, ride))


@router.post("/rides/{ride_id}", name="update_ride")
async def update_ride(request: Request, ride_id: int, account=Depends(require_account)):
    ride = ride_service.get_ride(ride_id)
    bike = bike_service.get_bike(ride.bike_id) if ride and ride.bike_id else None
    if ride is None or bike is None:
        return PlainTextResponse("Ride not found", status_code=404)
    form = await request.form()
    try:
        payload = _parse(form)
        if payload.bike_id is None:
            raise ValueError("Choose a bike.")
        ride_service.update_ride(
            ride_id, bike_id=payload.bike_id, day=payload.ride_date, time=payload.ride_time,
            miles=payload.miles, note=payload.note,
            moving_seconds=ride_service.parse_duration(payload.moving_time),
        )
    except ValidationError as exc:
        return _render(request, "rides/form.html", _form_context(bike, ride, error_context(form, exc)), status_code=422)
    except (ValueError, LookupError) as exc:
        message = "Choose a bike from the list." if isinstance(exc, LookupError) else str(exc)
        field = "bike_id" if isinstance(exc, LookupError) or message.startswith("Choose") else "miles"
        return _render(
            request, "rides/form.html", _form_context(bike, ride, message_context(form, message, field=field)),
            status_code=422,
        )
    return RedirectResponse(url=f"/bikes/{payload.bike_id}/rides", status_code=303)


@router.post("/rides/{ride_id}/delete", name="delete_ride")
def delete_ride(ride_id: int, account=Depends(require_account)):
    ride = ride_service.get_ride(ride_id)
    if ride is None:
        return PlainTextResponse("Ride not found", status_code=404)
    ride_service.delete_ride(ride_id)
    return RedirectResponse(url=f"/bikes/{ride.bike_id}/rides", status_code=303)


@router.get("/components/{component_id}/rides", name="component_rides")
def component_rides(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    trail = builder_service.breadcrumbs(f"component:{component_id}")
    crumbs = [*trail[:-1], (component.name, f"/components/{component_id}"), ("Rides", None)]
    return _render(
        request,
        "rides/log.html",
        {"log": ride_service.get_log_for_component(component_id), "component": component, "crumbs": crumbs},
    )


@router.get("/install-periods/{period_id}/rides", name="period_rides")
def period_rides(request: Request, period_id: int, from_bike: int | None = None, account=Depends(require_account)):
    """The rides that count toward one install period, read-only (specs/053-period-rides)."""
    try:
        log = ride_service.get_log_for_period(period_id)
    except LookupError:
        return PlainTextResponse("Installation period not found", status_code=404)
    if from_bike is not None and bike_service.get_bike(from_bike) is not None:
        trail = builder_service.breadcrumbs(f"bike:{from_bike}")
        back = (f"/bikes/{from_bike}/install-history")
        crumbs = [*trail[:-1], (trail[-1][0], f"/bikes/{from_bike}"), ("Install history", back), ("Rides", None)]
    else:
        trail = builder_service.breadcrumbs(f"component:{log.owner_id}")
        back = f"/components/{log.owner_id}/install-history"
        crumbs = [*trail[:-1], (trail[-1][0], f"/components/{log.owner_id}"), ("Install history", back), ("Rides", None)]
    return _render(request, "rides/log.html", {"log": log, "crumbs": crumbs})
