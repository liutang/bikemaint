"""Account settings routes: Strava connection status, reconnect, outbound webhook, and
notification lead time (User Stories 2 and 4).

Per Constitution Principle II, this module holds no business logic or direct DB
queries — it only translates HTTP concerns to/from `app/services/settings_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.models.form_errors import error_context
from app.models.requests import (
    LeadTimeSettingsRequest,
    SyncSettingsRequest,
    ThemeSettingsRequest,
    ClockSettingsRequest,
    TimezoneSettingsRequest,
    WebhookSettingsRequest,
)
from app.services import backup_service, clock_service, notification_service, settings_service
from app.services.auth_dependency import require_account

router = APIRouter()


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def _backup_context() -> dict:
    config = backup_service.rolling_config()
    if config is None:
        return {"enabled": False}
    folder, keep, hours = config
    return {"enabled": True, "dir": str(folder), "keep": keep, "hours": hours,
            "files": backup_service.describe_rolling_backups()}


def _is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"


def _settings_page(
    request: Request, account_id: int, context: dict | None = None, status_code: int = 200
):
    return _render(request, "settings/index.html", _page_context(account_id, context), status_code)


def _card(request: Request, account_id: int, card: str, context: dict | None = None):
    """One card re-rendered after an auto-save (specs/071): "Saved", or "Not saved" with the errors.

    Always 200, because HTMX only swaps successful answers; the card itself says what happened.
    """
    context = context or {}
    status = {"card_error": card} if context.get("errors") else {"saved": card}
    return _render(request, "settings/card.html", {**_page_context(account_id, context), **status, "card": card})


def _done(request: Request, account_id: int, card: str):
    """After a successful save: the card for HTMX, else back to Settings."""
    if _is_htmx(request):
        return _card(request, account_id, card)
    return RedirectResponse(url="/settings", status_code=303)


def _refused(request: Request, account_id: int, card: str, context: dict):
    if _is_htmx(request):
        return _card(request, account_id, card, context)
    return _settings_page(request, account_id, context, 422)


def _page_context(account_id: int, context: dict | None = None) -> dict:
    account = settings_service.get_account(account_id)
    page = {"errors": [], "field_errors": {}, "values": {}, **(context or {})}
    hours, minutes = settings_service.split_minutes(settings_service.effective_sync_interval(account))
    sync = {
        "interval_hours": hours,
        "interval_minutes": minutes,
        "interval_text": settings_service.describe_interval(settings_service.effective_sync_interval(account)),
    }
    choices = clock_service.timezone_choices(account.timezone)
    timezone_label = next(c["label"] for c in choices if c["value"] == account.timezone)
    return {
            "account": account,
            "sync": sync,
            "backup": _backup_context(),
            "timezone_choices": choices,
            "timezone_label": timezone_label.removeprefix("Current: "),
            **page,
    }


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
        return _refused(request, account.id, "strava", error_context(form, exc))
    settings_service.set_sync_settings(
        account.id, enabled=payload.sync_enabled, interval_minutes=payload.total_minutes
    )
    return _done(request, account.id, "strava")


@router.post("/settings/timezone", name="update_timezone_setting")
async def update_timezone_setting(request: Request, account=Depends(require_account)):
    """The zone UTC-recorded times are shown in (display only; specs/023)."""
    form = await request.form()
    try:
        payload = TimezoneSettingsRequest(timezone=form.get("timezone", ""))
    except ValidationError as exc:
        return _refused(request, account.id, "timezone", error_context(form, exc))
    settings_service.set_timezone(account.id, payload.timezone)
    return _done(request, account.id, "timezone")


@router.post("/settings/clock", name="update_clock_setting")
async def update_clock_setting(request: Request, account=Depends(require_account)):
    """12- or 24-hour display of times (display only; specs/036)."""
    form = await request.form()
    try:
        payload = ClockSettingsRequest(clock_format=form.get("clock_format", ""))
    except ValidationError as exc:
        return _refused(request, account.id, "clock", error_context(form, exc))
    settings_service.set_clock_format(account.id, payload.clock_format)
    return _done(request, account.id, "clock")


@router.post("/settings/notifications/mute", name="update_notification_mute")
async def update_notification_mute(request: Request, account=Depends(require_account)):
    """Mute all due-soon notifications and webhook posts (specs/045); a ticked box is present in the post."""
    form = await request.form()
    settings_service.set_notifications_muted(account.id, form.get("notifications_muted") is not None)
    return _done(request, account.id, "mute")


@router.post("/settings/notifications/test", name="test_notification")
def test_notification(request: Request, account=Depends(require_account)):
    """Send a test message to the saved webhook (specs/045). Always sent, even while muted."""
    url = settings_service.get_account(account.id).notification_webhook_url
    if not url:
        return _settings_page(
            request, account.id, {"test_result": {"ok": False, "message": "Save a webhook URL first, then send the test."}}, 422
        )
    delivered, error = notification_service.send_test(url)
    if delivered:
        return _settings_page(request, account.id, {"test_result": {"ok": True, "message": "Test notification delivered."}})
    return _settings_page(
        request, account.id,
        {"test_result": {"ok": False, "message": f"The test notification could not be delivered ({error})."}}, 502,
    )


@router.post("/settings/webhook", name="update_webhook_settings")
async def update_webhook_settings(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = WebhookSettingsRequest(
            notification_webhook_url=form.get("notification_webhook_url")
        )
    except ValidationError as exc:
        return _refused(request, account.id, "webhook", error_context(form, exc))
    settings_service.set_webhook_url(account.id, payload.notification_webhook_url)
    return _done(request, account.id, "webhook")


@router.post("/settings/notifications", name="update_notification_settings")
async def update_notification_settings(request: Request, account=Depends(require_account)):
    form = await request.form()
    try:
        payload = LeadTimeSettingsRequest(
            notification_lead_time_days=form.get("notification_lead_time_days", ""),
            lead_miles=form.get("lead_miles"),
            lead_rides=form.get("lead_rides"),
            lead_hours=form.get("lead_hours"),
        )
    except ValidationError as exc:
        return _refused(request, account.id, "lead", error_context(form, exc))
    settings_service.set_leads(
        account.id, days=payload.notification_lead_time_days,
        miles=payload.lead_miles, rides=payload.lead_rides, hours=payload.lead_hours,
    )
    return _done(request, account.id, "lead")


THEME_COOKIE = "theme"
ONE_YEAR_SECONDS = 365 * 24 * 60 * 60


@router.post("/settings/theme", name="update_theme_setting")
async def update_theme_setting(request: Request, account=Depends(require_account)):
    """The theme is a per-browser preference, so it lives in a cookie, not the database."""
    form = await request.form()
    try:
        payload = ThemeSettingsRequest(theme=form.get("theme", ""))
    except ValidationError as exc:
        return _refused(request, account.id, "appearance", error_context(form, exc))
    if _is_htmx(request):
        # The theme is applied when the page is drawn, so reload it (specs/071).
        response = _card(request, account.id, "appearance")
        response.headers["HX-Refresh"] = "true"
    else:
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
