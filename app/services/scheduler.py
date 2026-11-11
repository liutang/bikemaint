"""APScheduler background job: periodic Strava sync (research.md §7).

`app/main.py` starts/stops this on the FastAPI app's `startup`/`shutdown` events.
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.services import sync_service

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


def start() -> BackgroundScheduler:
    """Idempotent: returns the existing scheduler if already started."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    interval_minutes = int(os.environ.get("STRAVA_SYNC_INTERVAL_MINUTES", "30"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run_sync_job, "interval", minutes=interval_minutes, id="strava_sync")
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
