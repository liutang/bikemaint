"""Interactive bike builder routes (specs/004-bike-builder, M3).

Per Constitution Principle II, this module holds no business logic or direct DB queries: it
parses and validates input, delegates to `app/services/builder_service.py`, and renders. Every
action returns the whole `#builder` fragment for HTMX so the tree, storage list, palette and
valid targets refresh together; without HTMX it redirects (or re-renders the full page on error).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.models.requests import BuilderAddRequest, BuilderMoveRequest
from app.services import bike_service, builder_service
from app.services.auth_dependency import require_account
from app.services.component_service import ComponentNestingConflictError

router = APIRouter()

NOT_UNDERSTOOD = "That action was not understood, so nothing changed."


def _render(request: Request, bike_id: int, *, message: str | None = None, status_code: int = 200):
    view = builder_service.build_view(bike_id)
    if view is None:
        return PlainTextResponse("Bike not found", status_code=404)
    template = (
        "partials/builder.html" if request.headers.get("hx-request") == "true" else "bikes/build.html"
    )
    return request.app.state.templates.TemplateResponse(
        request, template, {"view": view, "bike": view.bike, "message": message}, status_code=status_code
    )


def _optional_text(form, name: str) -> str | None:
    value = form.get(name)
    return None if value is None or value == "" else value


def _done(request: Request, bike_id: int):
    if request.headers.get("hx-request") == "true":
        return _render(request, bike_id)
    return RedirectResponse(url=f"/bikes/{bike_id}/build", status_code=303)


@router.get("/bikes/{bike_id}/build", name="bike_builder")
def bike_builder(request: Request, bike_id: int, account=Depends(require_account)):
    return _render(request, bike_id)


@router.post("/bikes/{bike_id}/build/add", name="builder_add")
async def builder_add(request: Request, bike_id: int, account=Depends(require_account)):
    if bike_service.get_bike(bike_id) is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    try:
        payload = BuilderAddRequest(
            component_type=form.get("component_type", ""),
            target=form.get("target", ""),
            before_component_id=_optional_text(form, "before_component_id"),
        )
        builder_service.add_part(
            bike_id, payload.component_type, payload.parents(), payload.before_component_id
        )
    except ValidationError:
        return _render(request, bike_id, message=NOT_UNDERSTOOD, status_code=422)
    except (ComponentNestingConflictError, ValueError) as exc:
        return _render(request, bike_id, message=str(exc), status_code=422)
    return _done(request, bike_id)


@router.post("/bikes/{bike_id}/build/move", name="builder_move")
async def builder_move(request: Request, bike_id: int, account=Depends(require_account)):
    if bike_service.get_bike(bike_id) is None:
        return PlainTextResponse("Bike not found", status_code=404)
    form = await request.form()
    try:
        payload = BuilderMoveRequest(
            component_id=form.get("component_id", ""),
            target=form.get("target", ""),
            before_component_id=_optional_text(form, "before_component_id"),
        )
        builder_service.move_part(
            bike_id, payload.component_id, payload.parents(), payload.before_component_id
        )
    except ValidationError:
        return _render(request, bike_id, message=NOT_UNDERSTOOD, status_code=422)
    except (ComponentNestingConflictError, ValueError) as exc:
        return _render(request, bike_id, message=str(exc), status_code=422)
    return _done(request, bike_id)
