"""Account settings routes: Strava connection status, reconnect, outbound webhook, and
notification lead time (User Stories 2 and 4).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/settings_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.models.requests import LeadTimeSettingsRequest, WebhookSettingsRequest
from app.services import settings_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _settings_page(request: Request, account_id: int, errors: list[str], status_code: int = 200):
    account = settings_service.get_account(account_id)
    return _render(
        request, "settings/index.html", {"account": account, "errors": errors}, status_code
    )


@router.get("/settings", name="settings_index")
def settings_index(request: Request, account=Depends(require_account)):
    return _settings_page(request, account.id, [])


@router.post("/settings/strava/reconnect", name="strava_reconnect")
def strava_reconnect(request: Request, account=Depends(require_account)):
    # Re-initiates the OAuth flow via the existing /login page's authorize link.
    return RedirectResponse(url="/login", status_code=303)


@router.post("/settings/webhook", name="update_webhook_settings")
async def update_webhook_settings(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = WebhookSettingsRequest(
            notification_webhook_url=form.get("notification_webhook_url")
        )
    except ValidationError as exc:
        return _settings_page(request, account.id, [e["msg"] for e in exc.errors()], 422)
    settings_service.set_webhook_url(account.id, payload.notification_webhook_url)
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/notifications", name="update_notification_settings")
async def update_notification_settings(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = LeadTimeSettingsRequest(
            notification_lead_time_days=form.get("notification_lead_time_days", "")
        )
    except ValidationError as exc:
        return _settings_page(request, account.id, [e["msg"] for e in exc.errors()], 422)
    settings_service.set_lead_time_days(account.id, payload.notification_lead_time_days)
    return RedirectResponse(url="/settings", status_code=303)
