"""Unified bike/part screen actions (specs/005-unified-bike-screen).

Per Constitution Principle II, this module holds no business logic or direct DB queries: it
parses and validates input, delegates to `app/services/builder_service.py`, and renders. Every
action returns the whole `#builder` fragment for HTMX so the tree, storage list, palette and
valid targets refresh together; without HTMX it redirects (or re-renders the full page on error).
Actions that change the screen's own part (Garage or Trash on the part itself) redirect instead.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from app.models.requests import BuilderAddRequest, BuilderDeleteRequest, BuilderMoveRequest
from app.routers.screen import redirect_to, render_screen, screen_url
from app.services import builder_service
from app.services.auth_dependency import require_account
from app.services.component_service import (
    ComponentNestingConflictError,
    ConfirmationRequiredError,
)

router = APIRouter()

NOT_UNDERSTOOD = "That action was not understood, so nothing changed."


def _optional_text(form, name: str) -> str | None:
    value = form.get(name)
    return None if value is None or value == "" else value


def _root_of(form) -> str:
    return str(form.get("root", ""))


def _missing(root: str):
    return PlainTextResponse("Not found", status_code=404) if not builder_service.root_exists(root) else None


def _refuse(request: Request, root: str, message: str):
    return render_screen(request, root, message=message, status_code=422)


def _done(request: Request, root: str):
    if request.headers.get("hx-request") == "true":
        return render_screen(request, root)
    return redirect_to(request, screen_url(root))


@router.post("/builder/add", name="builder_add")
async def builder_add(request: Request, account=Depends(require_account)):
    form = await request.form()
    root = _root_of(form)
    if (missing := _missing(root)) is not None:
        return missing
    try:
        payload = BuilderAddRequest(
            root=root,
            component_type=form.get("component_type", ""),
            target=form.get("target", ""),
            before_component_id=_optional_text(form, "before_component_id"),
        )
        builder_service.add_part(
            payload.root, payload.component_type, payload.parents(), payload.before_component_id
        )
    except ValidationError:
        return _refuse(request, root, NOT_UNDERSTOOD)
    except (ComponentNestingConflictError, ValueError) as exc:
        return _refuse(request, root, str(exc))
    return _done(request, payload.root)


@router.post("/builder/move", name="builder_move")
async def builder_move(request: Request, account=Depends(require_account)):
    form = await request.form()
    root = _root_of(form)
    if (missing := _missing(root)) is not None:
        return missing
    try:
        payload = BuilderMoveRequest(
            root=root,
            component_id=form.get("component_id", ""),
            target=form.get("target", ""),
            before_component_id=_optional_text(form, "before_component_id"),
        )
        builder_service.move_part(
            payload.root, payload.component_id, payload.parents(), payload.before_component_id
        )
    except ValidationError:
        return _refuse(request, root, NOT_UNDERSTOOD)
    except (ComponentNestingConflictError, ValueError) as exc:
        return _refuse(request, root, str(exc))
    kind, root_id = builder_service.parse_root(payload.root)
    if kind == "component" and payload.component_id == root_id:
        # The part moved itself (Garage on its own screen): reload so the breadcrumb is right.
        return redirect_to(request, screen_url(payload.root))
    return _done(request, payload.root)


@router.post("/builder/delete", name="builder_delete")
async def builder_delete(request: Request, account=Depends(require_account)):
    form = await request.form()
    root = _root_of(form)
    if (missing := _missing(root)) is not None:
        return missing
    try:
        payload = BuilderDeleteRequest(
            root=root,
            component_id=form.get("component_id", ""),
            confirmed=form.get("confirmed") == "true",
        )
        crumbs = builder_service.breadcrumbs(payload.root)
        builder_service.delete_part(payload.root, payload.component_id, confirmed=payload.confirmed)
    except ValidationError:
        return _refuse(request, root, NOT_UNDERSTOOD)
    except ConfirmationRequiredError as exc:
        from app.services import component_service

        component = component_service.get_component(payload.component_id)
        confirm = {"component": component, "message": str(exc), "root": payload.root}
        return render_screen(request, payload.root, confirm=confirm)
    except (ComponentNestingConflictError, ValueError) as exc:
        return _refuse(request, root, str(exc))
    kind, root_id = builder_service.parse_root(payload.root)
    if kind == "component" and payload.component_id == root_id:
        # The part deleted itself: go to the level above (bike, ancestor part, or Storage).
        above = next((url for _, url in reversed(crumbs[:-1]) if url), "/")
        return redirect_to(request, above)
    return _done(request, payload.root)
