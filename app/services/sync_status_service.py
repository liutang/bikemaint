"""Human-readable "last synced" wording for the top-bar indicator.

Reads the time the last Strava sync run finished successfully (`account.strava_last_synced_at`),
which moves even when a run finds no new rides. Before any run is recorded it falls back to the
newest `ride_activity.synced_at`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db import accounts as accounts_db
from app.db import mileage
from app.db.connection import get_connection
from app.services import settings_service

_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_label(synced_at: str | None, *, now: datetime | None = None) -> str:
    if synced_at is None:
        return "Not synced yet"
    current = now or datetime.now(timezone.utc)
    synced = datetime.strptime(synced_at, _FORMAT).replace(tzinfo=timezone.utc)
    seconds = max(0, int((current - synced).total_seconds()))
    if seconds < 60:
        return "Synced just now"
    if seconds < 3600:
        return f"Synced {seconds // 60} min ago"
    if seconds < 86400:
        return f"Synced {seconds // 3600} h ago"
    return f"Synced {seconds // 86400} d ago"


def last_sync_label(*, now: datetime | None = None) -> str:
    with get_connection() as conn:
        account = accounts_db.get_singleton(conn)
        synced_at = account.strava_last_synced_at if account is not None else None
        if synced_at is None:
            synced_at = mileage.latest_synced_at(conn)
    return format_label(synced_at, now=now)


def sync_state(*, now: datetime | None = None) -> str:
    """Is sync working? `ok`, `error`, `off` or `unknown` (specs/003-cockpit-theme, FR-006b).

    Not working (`error`) when the Strava connection is stale, or when the last successful sync
    (else the time Strava was connected) is older than twice the sync interval. `off` when the
    rider turned automatic sync off. `unknown` when there is no account.
    """
    current = now or datetime.now(timezone.utc)
    with get_connection() as conn:
        account = accounts_db.get_singleton(conn)
        if account is None:
            return "unknown"
        if account.strava_connection_stale:
            return "error"
        if not account.strava_sync_enabled:
            return "off"
        synced_at = account.strava_last_synced_at or mileage.latest_synced_at(conn)
    reference = synced_at or account.strava_connected_at
    age = (current - datetime.strptime(reference, _FORMAT).replace(tzinfo=timezone.utc)).total_seconds()
    interval_minutes = settings_service.effective_sync_interval(account)
    return "error" if age > 2 * interval_minutes * 60 else "ok"
