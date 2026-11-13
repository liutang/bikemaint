"""APScheduler background jobs: periodic Strava sync and due-soon notification check
(research.md §7).

`app/main.py` starts/stops this on the FastAPI app's `startup`/`shutdown` events.
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.services import notification_service, sync_service

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_sync_job() -> None:
    with get_connection() as conn:
        account = accounts_db.get_singleton(conn)
    if account is None:
        return
    try:
        sync_service.sync_incremental(account.id)
    except Exception:
        logger.exception("scheduled Strava sync failed account_id=%s", account.id)


def _run_notification_job() -> None:
    try:
        notification_service.check_due_schedules()
    except Exception:
        logger.exception("scheduled due-soon notification check failed")


def default_sync_interval_minutes() -> int:
    """The server's interval (`STRAVA_SYNC_INTERVAL_MINUTES`, 30 if unset): used until the rider saves one."""
    return int(os.environ.get("STRAVA_SYNC_INTERVAL_MINUTES", "30"))


def _saved_sync_settings() -> tuple[bool, int]:
    """(automatic sync on, interval in minutes) from the account, else the defaults."""
    enabled, minutes = True, default_sync_interval_minutes()
    try:
        with get_connection() as conn:
            account = accounts_db.get_singleton(conn)
    except Exception:
        logger.warning("could not read the saved Strava sync settings; using the defaults")
        return enabled, minutes
    if account is not None:
        enabled = account.strava_sync_enabled
        if account.strava_sync_interval_minutes is not None:
            minutes = account.strava_sync_interval_minutes
    return enabled, minutes


def apply_sync_settings(enabled: bool, minutes: int) -> None:
    """Make the running scheduler follow the rider's setting at once (no restart).

    Off removes the sync job; on adds or replaces it in place, so exactly one exists.
    Does nothing when the scheduler is not running; `start()` reads the saved values.
    """
    if _scheduler is None:
        return
    if _scheduler.get_job("strava_sync") is not None:
        _scheduler.remove_job("strava_sync")
    if enabled:
        _scheduler.add_job(_run_sync_job, "interval", minutes=minutes, id="strava_sync")


def start() -> BackgroundScheduler:
    """Idempotent: returns the existing scheduler if already started."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    enabled, interval_minutes = _saved_sync_settings()
    scheduler = BackgroundScheduler()
    notification_interval_minutes = int(os.environ.get("NOTIFICATION_CHECK_INTERVAL_MINUTES", "60"))
    if enabled:
        scheduler.add_job(_run_sync_job, "interval", minutes=interval_minutes, id="strava_sync")
    scheduler.add_job(
        _run_notification_job,
        "interval",
        minutes=notification_interval_minutes,
        id="due_notifications",
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
