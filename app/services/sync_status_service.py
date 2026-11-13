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
