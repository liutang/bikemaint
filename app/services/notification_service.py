"""Due-soon notifications: dedup, in-app recording, and outbound webhook delivery (User Story 4).

Per Constitution Principle II this module is callable without FastAPI/request objects.
A `notification` row is unique per `(schedule_id, cycle_number)` (research.md §5), and a
failing webhook never prevents the in-app notification from being recorded (research.md §6).
"""

from __future__ import annotations

import logging
import time
from datetime import date

import httpx

from app.db import accounts as accounts_db
from app.db import notifications as notifications_db
from app.db.connection import get_connection
from app.models.rows import Notification
from app.services import schedule_service
from app.services.schedule_service import DueItem

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5.0
WEBHOOK_MAX_RETRIES = 2
WEBHOOK_BACKOFF_SECONDS = 1.0

_sleep = time.sleep  # indirection so tests can skip real backoff delays


def build_webhook_payload(item: DueItem) -> dict:
    """The JSON body described in contracts/webhook-payload.md."""
    projection = item.projection
    due = projection.due_at.isoformat() if projection.due_at else None
    status = "overdue" if projection.is_overdue else "due soon"
    summary = (
        f'🔧 Maintenance {status}: {item.schedule.name} on "{item.owner_name}" — '
        f"projected {due}"
    )
    if projection.remaining is not None:
        left = projection.remaining
        if projection.remaining_unit == "miles":
            summary += f" (approx. {left:.0f} mi remaining)"
        elif projection.remaining_unit == "hours":
            summary += f" (approx. {left:.1f} hours remaining)"
        else:
            summary += f" (approx. {left:.0f} {projection.remaining_unit} remaining)"
    return {
        "content": summary,
        "schedule": {
            "id": item.schedule.id,
            "name": item.schedule.name,
            "cycle_number": item.schedule.cycle_number,
            "owner_type": item.owner_type,
            "owner_id": item.owner_id,
            "owner_name": item.owner_name,
            "projected_due_at": due,
            "projected_remaining_miles": projection.remaining_miles,
            "projected_remaining": projection.remaining,
            "projected_remaining_unit": projection.remaining_unit,
            "is_low_confidence": projection.is_low_confidence,
        },
    }


def deliver_webhook(url: str, payload: dict) -> tuple[bool, str | None]:
    """POST `payload` to `url`; returns `(delivered, last_error)` and never raises.

    Tries once plus up to `WEBHOOK_MAX_RETRIES` retries; any 2xx counts as delivered. The
    URL itself is never logged, since webhook URLs (e.g. Discord's) embed a secret token.
    """
    error: str | None = None
    for attempt in range(WEBHOOK_MAX_RETRIES + 1):
        if attempt:
            _sleep(WEBHOOK_BACKOFF_SECONDS * 2 ** (attempt - 1))
        try:
            response = httpx.post(url, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            if response.is_success:
                return True, None
            error = f"HTTP {response.status_code}"
        logger.warning(
            "webhook delivery attempt failed attempt=%s of %s error=%s",
            attempt + 1,
            WEBHOOK_MAX_RETRIES + 1,
            error,
        )
    return False, error


def check_due_schedules(*, today: date | None = None) -> list[Notification]:
    """Notify for every active schedule newly inside the lead-time window (FR-015).

    Returns the notifications created by this call (already-notified cycles are skipped).
    """
    day = today or date.today()
    with get_connection() as conn:
        account = accounts_db.get_singleton(conn)
    if account is None:
        return []

    created: list[Notification] = []
    for item in schedule_service.list_due_overview(today=day):
        due_at = item.projection.due_at
        if not item.schedule.notify:
            continue  # the rider turned notifications off for this schedule (specs/040 FR-007)
        if due_at is None or (due_at - day).days > account.notification_lead_time_days:
            continue
        with get_connection() as conn:
            notification = notifications_db.insert(
                conn,
                schedule_id=item.schedule.id,
                cycle_number=item.schedule.cycle_number,
                projected_due_at=due_at.isoformat(),
            )
        if notification is None:
            continue  # already notified for this cycle
        logger.info(
            "recorded due-soon notification notification_id=%s schedule_id=%s cycle=%s due=%s",
            notification.id,
            item.schedule.id,
            item.schedule.cycle_number,
            due_at.isoformat(),
        )
        if account.notification_webhook_url:
            delivered, error = deliver_webhook(
                account.notification_webhook_url, build_webhook_payload(item)
            )
            with get_connection() as conn:
                notifications_db.record_webhook_result(
                    conn, notification.id, delivered=delivered, error=error
                )
                notification = notifications_db.get_by_id(conn, notification.id)
            if not delivered:
                logger.error(
                    "webhook delivery failed notification_id=%s schedule_id=%s error=%s",
                    notification.id,
                    item.schedule.id,
                    error,
                )
        created.append(notification)
    return created


def list_unacknowledged() -> list[Notification]:
    with get_connection() as conn:
        return notifications_db.list_unacknowledged(conn)


def acknowledge(notification_id: int) -> None:
    with get_connection() as conn:
        notifications_db.mark_acknowledged(conn, notification_id)
