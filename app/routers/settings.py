"""Account settings routes: Strava connection status, reconnect (User Story 2 slice).

Webhook/notification-lead-time settings are added later by User Story 4.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


@router.get("/settings", name="settings_index")
def settings_index(request: Request, account=Depends(require_account)):
    return _render(request, "settings/index.html", {"account": account})


@router.post("/settings/strava/reconnect", name="strava_reconnect")
def strava_reconnect(request: Request, account=Depends(require_account)):
    # Re-initiates the OAuth flow via the existing /login page's authorize link.
    return RedirectResponse(url="/login", status_code=303)
