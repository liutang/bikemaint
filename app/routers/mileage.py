"""Mileage routes: manual Strava sync trigger, manual mileage adjustments (User Story 2).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/sync_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.models.form_errors import message_context
from app.services import bike_service, component_service, sync_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _parse_delta_miles(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


@router.post("/sync/strava", name="trigger_strava_sync")
def trigger_strava_sync(request: Request, account=Depends(require_account)):
    sync_service.sync_incremental(account.id)
    return RedirectResponse(url="/", status_code=303)


@router.get("/bikes/{bike_id}/mileage/adjust", name="bike_mileage_adjust_form")
def bike_mileage_adjust_form(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(
        request, "mileage_adjust_form.html", {"item": bike, "item_kind": "bike", "errors": []}
    )


@router.post("/bikes/{bike_id}/mileage/adjust", name="adjust_bike_mileage")
async def adjust_bike_mileage(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    delta_miles = _parse_delta_miles(form.get("delta_miles"))
    if delta_miles is None:
        return _render(
            request,
            "mileage_adjust_form.html",
            {
                "item": bike,
                "item_kind": "bike",
                **message_context(
                    form, "Enter a numeric mileage adjustment.", field="delta_miles"
                ),
            },
            status_code=422,
        )
    sync_service.adjust_bike_mileage(bike_id, delta_miles=delta_miles, reason=form.get("reason") or None)
    return RedirectResponse(url=f"/bikes/{bike_id}", status_code=303)


@router.get("/components/{component_id}/mileage/adjust", name="component_mileage_adjust_form")
def component_mileage_adjust_form(
    request: Request, component_id: int, account=Depends(require_account)
):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    return _render(
        request,
        "mileage_adjust_form.html",
        {"item": component, "item_kind": "component", "errors": []},
    )


@router.post("/components/{component_id}/mileage/adjust", name="adjust_component_mileage")
async def adjust_component_mileage(
    request: Request, component_id: int, account=Depends(require_account)
):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    form = await request.form()
    delta_miles = _parse_delta_miles(form.get("delta_miles"))
    if delta_miles is None:
        return _render(
            request,
            "mileage_adjust_form.html",
            {
                "item": component,
                "item_kind": "component",
                **message_context(
                    form, "Enter a numeric mileage adjustment.", field="delta_miles"
                ),
            },
            status_code=422,
        )
    sync_service.adjust_component_mileage(
        component_id, delta_miles=delta_miles, reason=form.get("reason") or None
    )
    return RedirectResponse(url=f"/components/{component_id}", status_code=303)
