"""Sync rule routes for a bike's or part's Edit screen (specs/060-sync-rules).

Thin: the rule is validated and applied by `app/services/sync_rule_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.models import sync_rules as model
from app.services import bike_service, component_service, sync_rule_service
from app.services.auth_dependency import require_account

router = APIRouter()


def sync_context(kind: str, owner_id: int, *, error: str | None = None, submitted: dict | None = None) -> dict:
    """What the Sync rules section shows: the saved rule, or what was submitted when it was refused."""
    rule = sync_rule_service.get_rule(kind, owner_id)
    submitted = submitted or {}
    return {
        "sports": model.SPORTS,
        "ride_types": model.RIDE_TYPES,
        "chosen_sports": submitted.get("sports", rule.sports.split(",")),
        "chosen_types": submitted.get("ride_types", rule.ride_types.split(",")),
        "keywords": submitted.get("keywords", rule.keywords.replace(",", ", ")),
        "error": error,
    }


async def _save(request: Request, kind: str, owner_id: int):
    owner = bike_service.get_bike(owner_id) if kind == "bike" else component_service.get_component(owner_id)
    if owner is None:
        return PlainTextResponse(f"{kind.capitalize()} not found", status_code=404)
    form = await request.form()
    sports, types, keywords = form.getlist("sport"), form.getlist("ride_type"), form.get("keywords", "")
    try:
        sync_rule_service.save_rule(kind, owner_id, sports=sports, ride_types=types, keywords=keywords)
    except ValueError as exc:
        # Re-show the Edit screen with the message beside the rules (imported here: the form
        # contexts live in the owners' own routers).
        if kind == "bike":
            from app.routers.bikes import _form_context
            template, context = "bikes/form.html", _form_context(owner)
        else:
            from app.routers.components import _form_context
            template, context = "components/form.html", _form_context(
                owner, owner.parent_bike_id, owner.parent_component_id
            )
        context["sync"] = sync_context(
            kind, owner_id, error=str(exc), submitted={"sports": sports, "ride_types": types, "keywords": keywords}
        )
        return request.app.state.templates.TemplateResponse(request, template, context, status_code=422)
    return RedirectResponse(url=f"/{kind}s/{owner_id}/edit", status_code=303)


@router.post("/bikes/{bike_id}/sync-rules", name="save_bike_sync_rules")
async def save_bike_sync_rules(request: Request, bike_id: int, account=Depends(require_account)):
    return await _save(request, "bike", bike_id)


@router.post("/components/{component_id}/sync-rules", name="save_component_sync_rules")
async def save_component_sync_rules(request: Request, component_id: int, account=Depends(require_account)):
    return await _save(request, "component", component_id)
