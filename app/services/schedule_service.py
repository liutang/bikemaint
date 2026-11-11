"""Business logic for maintenance schedules: due-date projection and completion (User Story 4).

Per Constitution Principle II this module is callable without FastAPI/request objects.
Projected due dates are computed on read and never stored (research.md §4), so they always
reflect current pace, installed status, and parent bike (FR-017).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db import schedules as schedules_db
from app.db.connection import get_connection
from app.models.rows import MaintenanceSchedule
from app.services import maintenance_service

logger = logging.getLogger(__name__)

# Trailing window for the riding-pace estimate (research.md §4).
PACE_WINDOW_DAYS = 90
# Minimum number of distinct days with a ride inside the window before a mileage-based
# projection is trusted (research.md §4's "configurable minimum of ride-days").
MIN_RIDE_DAYS_FOR_CONFIDENCE = 5


@dataclass(frozen=True)
class Projection:
    due_at: date | None
    remaining_miles: float | None
    is_low_confidence: bool
    is_overdue: bool


@dataclass(frozen=True)
class DueItem:
    schedule: MaintenanceSchedule
    owner_type: str  # "bike" | "component"
    owner_id: int
    owner_name: str
    projection: Projection
    status: str  # overdue | due_soon | on_track | no_estimate (see `due_status`)
    days_until: int | None = None  # days to the projected date; negative = days late
    bike_name: str | None = None  # the bike a part schedule's part is on (None for bike schedules)
    ring: float = 0.0  # progress-ring fill, 0..1 (see `ring_fraction`)


DEFAULT_LEAD_TIME_DAYS = 7


def due_status(projection: Projection, lead_time_days: int, today: date) -> str:
    """Dashboard status for a projection: overdue, due_soon, on_track or no_estimate.

    `due_soon` mirrors the notification rule: not overdue and due within `lead_time_days`.
    """
    if projection.is_overdue:
        return "overdue"
    if projection.due_at is None:
        return "no_estimate"
    if (projection.due_at - today).days <= lead_time_days:
        return "due_soon"
    return "on_track"


URGENT_STATUSES = ("overdue", "due_soon")
MAX_URGENT_TILES = 6
RING_FLOOR = 0.08  # a due-soon ring always shows at least a sliver of arc


def ring_fraction(status: str, days_until: int | None, lead_time_days: int) -> float:
    """How full a task's progress ring is: overdue is full, due soon grows as the date nears."""
    if status == "overdue":
        return 1.0
    if status != "due_soon":
        return 0.0
    if days_until is None or days_until <= 0 or lead_time_days <= 0:
        return 1.0
    return min(1.0, max(RING_FLOOR, 1 - days_until / lead_time_days))


@dataclass(frozen=True)
class Attention:
    shown: list[DueItem]  # urgent cards to display, most urgent first
    overflow_count: int  # urgent tasks collapsed into the "+N more" tile
    urgent_total: int
    others: list[DueItem]  # on track / no estimate, for the compact list


def split_attention(
    items: list[DueItem], *, show_all: bool = False, limit: int = MAX_URGENT_TILES
) -> Attention:
    """Split the overview into urgent cards (capped at `limit` tiles) and everything else."""
    overdue = sorted(
        (i for i in items if i.status == "overdue"),
        key=lambda i: (min(i.days_until or 0, 0), i.schedule.id),
    )
    due_soon = sorted(
        (i for i in items if i.status == "due_soon"),
        key=lambda i: (i.days_until if i.days_until is not None else 0, i.schedule.id),
    )
    urgent = overdue + due_soon
    others = sorted(
        (i for i in items if i.status not in URGENT_STATUSES),
        key=lambda i: (i.days_until is None, i.days_until or 0, i.schedule.id),
    )
    if show_all or len(urgent) <= limit:
        return Attention(urgent, 0, len(urgent), others)
    shown = urgent[: limit - 1]
    return Attention(shown, len(urgent) - len(shown), len(urgent), others)


def _today(today: date | None) -> date:
    return today or date.today()


def _validate(
    *, bike_id: int | None, component_id: int | None, interval_miles, interval_days
) -> None:
    if (bike_id is None) == (component_id is None):
        raise ValueError("A schedule must belong to exactly one of a bike or a component.")
    if interval_miles is None and interval_days is None:
        raise ValueError("A schedule needs a mileage interval, a time interval, or both.")


def _owner(conn, schedule: MaintenanceSchedule):
    """The bike/component a schedule belongs to, or None if it has been deleted."""
    if schedule.bike_id is not None:
        return bikes_db.get_by_id(conn, schedule.bike_id)
    return components_db.get_by_id(conn, schedule.component_id)


def _top_bike_id(conn, schedule: MaintenanceSchedule) -> int | None:
    """The bike whose riding pace drives this schedule, or None for a component in storage."""
    if schedule.bike_id is not None:
        return schedule.bike_id
    component = components_db.get_by_id(conn, schedule.component_id)
    if component is None:
        return None
    if component.parent_bike_id is not None:
        return component.parent_bike_id
    if component.parent_component_id is not None:
        return components_db.resolve_top_bike_id(conn, component.parent_component_id)
    return None


def create_schedule(
    *,
    bike_id: int | None = None,
    component_id: int | None = None,
    name: str,
    interval_miles: float | None = None,
    interval_days: int | None = None,
    today: date | None = None,
) -> MaintenanceSchedule:
    _validate(
        bike_id=bike_id,
        component_id=component_id,
        interval_miles=interval_miles,
        interval_days=interval_days,
    )
    with get_connection() as conn:
        owner = (
            bikes_db.get_by_id(conn, bike_id)
            if bike_id is not None
            else components_db.get_by_id(conn, component_id)
        )
        if owner is None:
            raise LookupError("No such bike or component to schedule maintenance for.")
        return schedules_db.create(
            conn,
            bike_id=bike_id,
            component_id=component_id,
            name=name,
            interval_miles=interval_miles,
            interval_days=interval_days,
            baseline_mileage=owner.total_mileage,
            baseline_date=_today(today).isoformat(),
        )


def get_schedule(schedule_id: int) -> MaintenanceSchedule | None:
    with get_connection() as conn:
        return schedules_db.get_by_id(conn, schedule_id)


def list_for_bike(bike_id: int) -> list[MaintenanceSchedule]:
    with get_connection() as conn:
        return schedules_db.list_active_for_bike(conn, bike_id)


def list_for_component(component_id: int) -> list[MaintenanceSchedule]:
    with get_connection() as conn:
        return schedules_db.list_active_for_component(conn, component_id)


def update_schedule(
    schedule_id: int,
    *,
    name: str,
    interval_miles: float | None,
    interval_days: int | None,
    is_active: bool = True,
) -> MaintenanceSchedule:
    if interval_miles is None and interval_days is None:
        raise ValueError("A schedule needs a mileage interval, a time interval, or both.")
    with get_connection() as conn:
        if schedules_db.get_by_id(conn, schedule_id) is None:
            raise LookupError(f"No schedule with id {schedule_id}")
        return schedules_db.update(
            conn,
            schedule_id,
            name=name,
            interval_miles=interval_miles,
            interval_days=interval_days,
            is_active=is_active,
        )


def delete_schedule(schedule_id: int) -> None:
    """Stop projecting/notifying; completed-cycle history in the maintenance log is kept."""
    with get_connection() as conn:
        if schedules_db.get_by_id(conn, schedule_id) is None:
            raise LookupError(f"No schedule with id {schedule_id}")
        schedules_db.deactivate(conn, schedule_id)


def _trailing_pace(conn, bike_id: int | None, today: date) -> tuple[float, int]:
    """(miles per day, distinct ride days) for a bike over the trailing window."""
    if bike_id is None:
        return 0.0, 0
    since = datetime.combine(
        today - timedelta(days=PACE_WINDOW_DAYS), datetime.min.time(), tzinfo=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    miles, ride_days = mileage_db.recent_ride_stats_for_bike(conn, bike_id, since=since)
    return miles / PACE_WINDOW_DAYS, ride_days


def _project(conn, schedule: MaintenanceSchedule, today: date) -> Projection:
    owner = _owner(conn, schedule)
    current_mileage = owner.total_mileage if owner is not None else schedule.baseline_mileage

    time_due: date | None = None
    if schedule.interval_days is not None:
        time_due = date.fromisoformat(schedule.baseline_date) + timedelta(
            days=schedule.interval_days
        )

    mileage_due: date | None = None
    mileage_trusted = False
    remaining: float | None = None
    mileage_exceeded = False
    if schedule.interval_miles is not None:
        remaining = schedule.baseline_mileage + schedule.interval_miles - current_mileage
        pace, ride_days = _trailing_pace(conn, _top_bike_id(conn, schedule), today)
        if remaining <= 0:
            mileage_exceeded = True
            mileage_due = today
            mileage_trusted = True  # already past the interval: no pace needed to know that
        elif pace > 0:
            mileage_due = today + timedelta(days=math.ceil(remaining / pace - 1e-9))
            mileage_trusted = ride_days >= MIN_RIDE_DAYS_FOR_CONFIDENCE
        remaining = max(remaining, 0.0)

    if mileage_trusted:
        candidates = [d for d in (mileage_due, time_due) if d is not None]
        due_at, low_confidence = min(candidates), False
    elif time_due is not None:
        # Not enough riding history to trust the mileage side: time-only fallback (FR-018).
        due_at, low_confidence = time_due, False
    else:
        due_at, low_confidence = mileage_due, True

    is_overdue = mileage_exceeded or (time_due is not None and time_due < today)
    return Projection(
        due_at=due_at,
        remaining_miles=remaining,
        is_low_confidence=low_confidence,
        is_overdue=is_overdue,
    )


def project_due_date(schedule: MaintenanceSchedule, *, today: date | None = None) -> Projection:
    with get_connection() as conn:
        return _project(conn, schedule, _today(today))


def _bike_name_for_part(conn, schedule: MaintenanceSchedule) -> str | None:
    """The name of the bike a part schedule's part is installed on, if any."""
    if schedule.component_id is None:
        return None
    bike_id = _top_bike_id(conn, schedule)
    bike = bikes_db.get_by_id(conn, bike_id) if bike_id is not None else None
    return bike.name if bike else None


def _due_item(
    conn, schedule: MaintenanceSchedule, today: date, lead_time_days: int
) -> DueItem | None:
    owner = _owner(conn, schedule)
    if owner is None:
        return None  # the bike/component was deleted; nothing to project
    projection = _project(conn, schedule, today)
    status = due_status(projection, lead_time_days, today)
    days_until = (projection.due_at - today).days if projection.due_at is not None else None
    return DueItem(
        schedule=schedule,
        owner_type="bike" if schedule.bike_id is not None else "component",
        owner_id=owner.id,
        owner_name=owner.name,
        projection=projection,
        status=status,
        days_until=days_until,
        bike_name=_bike_name_for_part(conn, schedule),
        ring=ring_fraction(status, days_until, lead_time_days),
    )


def get_due_item(
    schedule_id: int, *, today: date | None = None, lead_time_days: int = DEFAULT_LEAD_TIME_DAYS
) -> DueItem | None:
    with get_connection() as conn:
        schedule = schedules_db.get_by_id(conn, schedule_id)
        if schedule is None or not schedule.is_active:
            return None
        return _due_item(conn, schedule, _today(today), lead_time_days)


def list_due_overview(
    *, today: date | None = None, lead_time_days: int = DEFAULT_LEAD_TIME_DAYS
) -> list[DueItem]:
    """Every active schedule in the garage, most urgent first (FR-019)."""
    day = _today(today)
    with get_connection() as conn:
        items = [
            item
            for schedule in schedules_db.list_all_active(conn)
            if (item := _due_item(conn, schedule, day, lead_time_days)) is not None
        ]
    return sorted(
        items,
        key=lambda i: (i.projection.due_at is None, i.projection.due_at or date.max, i.schedule.id),
    )


def complete_schedule(schedule_id: int, *, today: date | None = None) -> MaintenanceSchedule:
    """Check off a schedule: log the maintenance and start the next cycle (FR-016)."""
    day = _today(today)
    with get_connection() as conn:
        schedule = schedules_db.get_by_id(conn, schedule_id)
        if schedule is None:
            raise LookupError(f"No schedule with id {schedule_id}")

    entry = maintenance_service.log_maintenance(
        bike_id=schedule.bike_id,
        component_id=schedule.component_id,
        description=schedule.name,
        performed_at=day.isoformat(),
        schedule_id=schedule.id,
    )
    with get_connection() as conn:
        completed = schedules_db.complete(
            conn,
            schedule_id,
            baseline_mileage=entry.mileage_at_service,
            baseline_date=day.isoformat(),
        )
    logger.info(
        "completed maintenance schedule schedule_id=%s name=%r new_cycle=%s",
        schedule_id,
        schedule.name,
        completed.cycle_number,
    )
    return completed
