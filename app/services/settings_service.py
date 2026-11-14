"""Business logic for account settings: outbound webhook URL and notification lead time (FR-023)."""

from __future__ import annotations

import logging

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account
from app.services import clock_service, scheduler

logger = logging.getLogger(__name__)


def get_account(account_id: int) -> Account:
    with get_connection() as conn:
        account = accounts_db.get_by_id(conn, account_id)
    if account is None:
        raise LookupError(f"No account with id {account_id}")
    return account


def set_webhook_url(account_id: int, url: str | None) -> None:
    with get_connection() as conn:
        accounts_db.update_webhook_url(conn, account_id, url)


def set_lead_time_days(account_id: int, days: int) -> None:
    with get_connection() as conn:
        accounts_db.update_lead_time_days(conn, account_id, days)


def set_sync_settings(account_id: int, *, enabled: bool, interval_minutes: int) -> None:
    """Save the automatic Strava sync switch and interval and apply them to the running scheduler."""
    with get_connection() as conn:
        accounts_db.update_sync_settings(
            conn, account_id, enabled=enabled, interval_minutes=interval_minutes
        )
    scheduler.apply_sync_settings(enabled, interval_minutes)
    logger.info(
        "Strava sync settings changed account_id=%s enabled=%s interval_minutes=%s",
        account_id, enabled, interval_minutes,
    )


def effective_sync_interval(account: Account) -> int:
    """The saved interval, else the server's default (`STRAVA_SYNC_INTERVAL_MINUTES`, 30)."""
    if account.strava_sync_interval_minutes is not None:
        return account.strava_sync_interval_minutes
    return scheduler.default_sync_interval_minutes()


def split_minutes(minutes: int) -> tuple[int, int]:
    """Total minutes as (hours, minutes) for the form."""
    return minutes // 60, minutes % 60


def describe_interval(minutes: int) -> str:
    """"1 h 30 min", "45 min", "2 h"."""
    hours, rest = split_minutes(minutes)
    parts = ([f"{hours} h"] if hours else []) + ([f"{rest} min"] if rest else [])
    return " ".join(parts) or "0 min"


def set_timezone(account_id: int, timezone: str) -> None:
    """Save the time zone used to show UTC-recorded times (display only)."""
    with get_connection() as conn:
        accounts_db.update_timezone(conn, account_id, timezone)
    clock_service.remember_zone(timezone)


def set_clock_format(account_id: int, clock_format: str) -> None:
    """Save 12- or 24-hour display of times (display only; specs/036)."""
    with get_connection() as conn:
        accounts_db.update_clock_format(conn, account_id, clock_format)
    clock_service.remember_clock(clock_format)


def set_notifications_muted(account_id: int, muted: bool) -> None:
    """Mute or unmute all due-soon notifications and webhook posts (specs/045)."""
    with get_connection() as conn:
        accounts_db.update_notifications_muted(conn, account_id, muted)

