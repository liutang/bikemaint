"""Account settings routes: Strava connection status, reconnect, outbound webhook, and
notification lead time (User Stories 2 and 4).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/settings_service.py`.
"""

from __future__ import annotations

from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.models.form_errors import error_context
from app.models.requests import (
    LeadTimeSettingsRequest,
    SyncSettingsRequest,
    ThemeSettingsRequest,
    TimezoneSettingsRequest,
    WebhookSettingsRequest,
)
from app.services import settings_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _settings_page(
    request: Request, account_id: int, context: dict | None = None, status_code: int = 200
):
    account = settings_service.get_account(account_id)
    page = {"errors": [], "field_errors": {}, "values": {}, **(context or {})}
    hours, minutes = settings_service.split_minutes(settings_service.effective_sync_interval(account))
    sync = {
        "interval_hours": hours,
        "interval_minutes": minutes,
        "interval_text": settings_service.describe_interval(settings_service.effective_sync_interval(account)),
    }
    return _render(
        request,
        "settings/index.html",
        {"account": account, "sync": sync, "timezones": sorted(available_timezones()), **page},
        status_code,
    )


@router.get("/settings", name="settings_index")
def settings_index(request: Request, account=Depends(require_account)):
    return _settings_page(request, account.id)


@router.post("/settings/strava/reconnect", name="strava_reconnect")
def strava_reconnect(request: Request, account=Depends(require_account)):
    # Re-initiates the OAuth flow via the existing /login page's authorize link.
    return RedirectResponse(url="/login", status_code=303)


@router.post("/settings/strava/sync", name="update_strava_sync_settings")
async def update_strava_sync_settings(request: Request, account=Depends(require_account)):
    """Automatic Strava sync on/off and its interval (specs/023-settings-sync-and-timezone)."""
    form = await request.form()
    try:
        payload = SyncSettingsRequest(
            sync_enabled=form.get("sync_enabled") is not None,
            interval_hours=form.get("interval_hours", ""),
            interval_minutes=form.get("interval_minutes", ""),
        )
    except ValidationError as exc:
        return _settings_page(request, account.id, error_context(form, exc), 422)
    settings_service.set_sync_settings(
        account.id, enabled=payload.sync_enabled, interval_minutes=payload.total_minutes
    )
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/timezone", name="update_timezone_setting")
async def update_timezone_setting(request: Request, account=Depends(require_account)):
    """The zone UTC-recorded times are shown in (display only; specs/023)."""
    form = await request.form()
    try:
        payload = TimezoneSettingsRequest(timezone=form.get("timezone", ""))
    except ValidationError as exc:
        return _settings_page(request, account.id, error_context(form, exc), 422)
    settings_service.set_timezone(account.id, payload.timezone)
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/webhook", name="update_webhook_settings")
async def update_webhook_settings(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = WebhookSettingsRequest(
            notification_webhook_url=form.get("notification_webhook_url")
        )
    except ValidationError as exc:
        return _settings_page(request, account.id, error_context(form, exc), 422)
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
        return _settings_page(request, account.id, error_context(form, exc), 422)
    settings_service.set_lead_time_days(account.id, payload.notification_lead_time_days)
    return RedirectResponse(url="/settings", status_code=303)


THEME_COOKIE = "theme"
ONE_YEAR_SECONDS = 365 * 24 * 60 * 60


@router.post("/settings/theme", name="update_theme_setting")
async def update_theme_setting(request: Request, account=Depends(require_account)):
    """The theme is a per-browser preference, so it lives in a cookie, not the database."""
    form = await request.form()
    try:
        payload = ThemeSettingsRequest(theme=form.get("theme", ""))
    except ValidationError as exc:
        return _settings_page(request, account.id, error_context(form, exc), 422)
    response = RedirectResponse(url="/settings", status_code=303)
    response.set_cookie(
        THEME_COOKIE,
        payload.theme,
        max_age=ONE_YEAR_SECONDS,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response
