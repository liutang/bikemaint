"""Bike routes: garage overview, bike detail, create/edit/delete (User Story 1).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/bike_service.py`
and `app/services/component_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import BikeCreateRequest, BikeUpdateRequest
from app.services import bike_service, component_service, strava_client
from app.services.auth_dependency import require_account

router = APIRouter()


def _optional_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


@router.get("/", name="garage_overview")
def garage_overview(request: Request, account=Depends(require_account)):
    bikes = bike_service.list_bikes()
    in_storage_components = component_service.list_in_storage()
    return _render(
        request,
        "bikes/list.html",
        {"bikes": bikes, "in_storage_components": in_storage_components},
    )


@router.get("/bikes/new", name="new_bike_form")
def new_bike_form(request: Request, account=Depends(require_account)):
    return _render(request, "bikes/form.html", {"bike": None, "errors": []})


@router.post("/bikes", name="create_bike")
async def create_bike(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = BikeCreateRequest(
            name=form.get("name", ""),
            bike_type=form.get("bike_type") or None,
            manual_baseline_mileage=_optional_float(form.get("manual_baseline_mileage")),
        )
    except ValidationError as exc:
        return _render(
            request,
            "bikes/form.html",
            {"bike": None, "errors": [error["msg"] for error in exc.errors()]},
            status_code=422,
        )
    bike = bike_service.create_bike(**payload.model_dump())
    if request.headers.get("hx-request") == "true":
        return _render(request, "bikes/list.html", {
            "bikes": bike_service.list_bikes(),
            "in_storage_components": component_service.list_in_storage(),
        })
    return RedirectResponse(url=f"/bikes/{bike.id}", status_code=303)


@router.get("/bikes/{bike_id}", name="bike_detail")
def bike_detail(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    all_components = component_service.get_tree_for_bike(bike_id)
    top_level = [c for c in all_components if c.parent_bike_id == bike_id]
    tree = component_service.build_tree(top_level, all_components)
    return _render(request, "bikes/detail.html", {"bike": bike, "tree": tree})


@router.get("/bikes/{bike_id}/edit", name="edit_bike_form")
def edit_bike_form(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    return _render(request, "bikes/form.html", {"bike": bike, "errors": []})


@router.post("/bikes/{bike_id}", name="update_bike")
async def update_bike(request: Request, bike_id: int, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = BikeUpdateRequest(
            name=form.get("name", ""),
            bike_type=form.get("bike_type") or None,
            manual_baseline_mileage=_optional_float(form.get("manual_baseline_mileage")),
        )
    except ValidationError as exc:
        bike = bike_service.get_bike(bike_id)
        return _render(
            request,
            "bikes/form.html",
            {"bike": bike, "errors": [error["msg"] for error in exc.errors()]},
            status_code=422,
        )
    bike = bike_service.update_bike(bike_id, **payload.model_dump())
    return RedirectResponse(url=f"/bikes/{bike.id}", status_code=303)


@router.get("/bikes/{bike_id}/strava-pairing", name="strava_pairing_form")
def strava_pairing_form(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    try:
        access_token = strava_client.ensure_fresh_access_token(account)
        gear = bike_service.unpaired_gear(strava_client.get_athlete_gear(access_token))
    except strava_client.StravaTokenRefreshError:
        gear = []
    return _render(request, "bikes/strava_pairing.html", {"bike": bike, "gear": gear, "errors": []})


@router.post("/bikes/{bike_id}/strava-pairing", name="pair_bike_to_strava_gear")
async def pair_bike_to_strava_gear(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    strava_gear_id = form.get("strava_gear_id") or ""
    if not strava_gear_id:
        return _render(
            request,
            "bikes/strava_pairing.html",
            {"bike": bike, "gear": [], "errors": ["Choose a Strava gear entry."]},
            status_code=422,
        )
    updated = bike_service.pair_to_strava_gear(bike_id, strava_gear_id)
    return RedirectResponse(url=f"/bikes/{updated.id}", status_code=303)


@router.post("/bikes/{bike_id}/delete", name="delete_bike")
async def delete_bike(request: Request, bike_id: int, account=Depends(require_account)):
    form = await request.form()
    confirmed = form.get("confirmed") == "true"
    try:
        bike_service.delete_bike(bike_id, confirmed=confirmed)
    except bike_service.ConfirmationRequiredError as exc:
        return _render(
            request,
            "partials/confirm_delete.html",
            {"item_type": "bike", "message": str(exc), "action": f"/bikes/{bike_id}/delete"},
        )
    if request.headers.get("hx-request") == "true":
        return _render(request, "bikes/list.html", {
            "bikes": bike_service.list_bikes(),
            "in_storage_components": component_service.list_in_storage(),
        })
    return RedirectResponse(url="/", status_code=303)
