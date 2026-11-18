"""Archive and unarchive routes (specs/079 contracts/routes.md).

Holds no business logic: it translates the form to `archive_service` and re-renders the Edit
screen when the request is refused.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import ArchiveRequest
from app.services import archive_service, bike_service, component_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _attached(form) -> str | None:
    try:
        return ArchiveRequest(attached=form.get("attached", "")).attached
    except ValidationError:
        return None  # an unknown choice counts as no choice; the service asks for one


def _bike_form(request: Request, bike, message: str, status_code: int):
    from app.routers.bikes import _form_context, _render

    return _render(request, "bikes/form.html", _form_context(bike, {"errors": [message]}), status_code=status_code)


def _part_form(request: Request, component, message: str, status_code: int):
    from app.routers.components import edit_form_response

    return edit_form_response(request, component, errors=[message], status_code=status_code)


@router.post("/bikes/{bike_id}/archive", name="archive_bike")
async def archive_bike(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    try:
        archive_service.archive_bike(bike_id, _attached(form))
    except archive_service.ArchivedError as exc:
        return _bike_form(request, bike, str(exc), 409)
    except ValueError as exc:
        return _bike_form(request, bike, str(exc), 422)
    return RedirectResponse(url="/", status_code=303)


@router.post("/bikes/{bike_id}/unarchive", name="unarchive_bike")
async def unarchive_bike(request: Request, bike_id: int, account=Depends(require_account)):
    bike = bike_service.get_bike(bike_id)
    if bike is None:
        return PlainTextResponse("Bike not found", status_code=404)
    try:
        archive_service.unarchive_bike(bike_id)
    except ValueError as exc:
        return _bike_form(request, bike, str(exc), 409)
    return RedirectResponse(url=f"/bikes/{bike_id}/edit", status_code=303)


@router.post("/components/{component_id}/archive", name="archive_component")
async def archive_component(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    form = await request.form()
    try:
        archive_service.archive_part(component_id, _attached(form))
    except archive_service.ArchivedError as exc:
        return _part_form(request, component, str(exc), 409)
    except ValueError as exc:
        return _part_form(request, component, str(exc), 422)
    return RedirectResponse(url="/components", status_code=303)


@router.post("/components/{component_id}/unarchive", name="unarchive_component")
async def unarchive_component(request: Request, component_id: int, account=Depends(require_account)):
    component = component_service.get_component(component_id)
    if component is None:
        return PlainTextResponse("Component not found", status_code=404)
    try:
        archive_service.unarchive_part(component_id)
    except ValueError as exc:
        return _part_form(request, component, str(exc), 409)
    return RedirectResponse(url=f"/components/{component_id}/edit", status_code=303)
