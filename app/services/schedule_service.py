"""Business logic for maintenance schedules: due-date projection and completion (User Story 4).

Per Constitution Principle II this module is callable without FastAPI/request objects.
Projected due dates are computed on read and never stored (research.md §4), so they always
reflect current pace, installed status, and parent bike (FR-017).
"""

from __future__ import annotations

import calendar
import logging
import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db import schedules as schedules_db
from app.db.connection import get_connection
from app.models.rows import MaintenanceSchedule
from app.models.schedule_kinds import PERIOD_UNITS, SERVICE_TYPES, USAGE_UNITS, WHOLE_UNITS
from app.db import maintenance as maintenance_db
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
    remaining: float | None = None  # usage left, in `remaining_unit` (specs/040)
    remaining_unit: str | None = None  # "miles" | "rides" | "hours"
    over: float | None = None  # how far past a usage interval, in `remaining_unit` (specs/040 FR-012)


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


def add_period(start: date, value: int, unit: str) -> date:
    """`start` plus `value` calendar years, months or weeks (a day past a short month's end clamps)."""
    if unit == "weeks":
        return start + timedelta(weeks=value)
    months = value * 12 if unit == "years" else value
    index = start.year * 12 + start.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def _now_stored() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _typed_fields(service_type, interval_kind, interval_value, interval_unit) -> dict:
    """Check a feature-040 schedule definition; returns the values to store (incl. old columns)."""
    if service_type not in SERVICE_TYPES:
        raise ValueError("Choose a service type: " + ", ".join(SERVICE_TYPES) + ".")
    allowed = USAGE_UNITS if interval_kind == "usage" else PERIOD_UNITS if interval_kind == "period" else ()
    if interval_unit not in allowed:
        raise ValueError("That unit does not fit the interval kind.")
    if interval_value is None or interval_value <= 0:
        raise ValueError("The interval must be more than zero.")
    if interval_unit in WHOLE_UNITS and interval_value != int(interval_value):
        raise ValueError(f"Use a whole number of {interval_unit}.")
    return {
        "name": service_type,
        "service_type": service_type,
        "interval_kind": interval_kind,
        "interval_value": float(interval_value),
        "interval_unit": interval_unit,
        # miles and weeks also fill the older columns, which the due-date maths already reads
        "interval_miles": float(interval_value) if interval_unit == "miles" else None,
        "interval_days": int(interval_value) * 7 if interval_unit == "weeks" else None,
    }


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


def _baseline_for(conn, owner, *, bike_id, component_id, service_type: str, today: date) -> dict:
    """Where a new schedule starts counting (specs/040 FR-011).

    From the latest logged maintenance of the same service type on this bike or part: its date and
    time, the mileage recorded on it, and the rides and hours after it. If there is none, from when
    tracking began: all rides (not the starting mileage) and, for a period, the earliest install
    date of a part, else when the bike or part was added.
    """
    entry = maintenance_db.latest_for_owner_and_type(
        conn, bike_id=bike_id, component_id=component_id, service_type=service_type
    )
    if entry is not None:
        return {
            "baseline_mileage": entry.mileage_at_service,
            "baseline_date": entry.performed_at,
            "baseline_at": maintenance_service.entry_moment(entry),
        }
    # created_at is UTC; compare it with "today" the way the rest of the module does (server-local)
    started = datetime.fromisoformat(owner.created_at.replace("Z", "+00:00")).astimezone().date().isoformat()
    if component_id is not None:
        installs = [p.installed_at[:10] for p in components_db.list_periods(conn, component_id)]
        if installs:
            started = min(installs)
    return {
        "baseline_mileage": owner.manual_baseline_mileage,
        "baseline_date": started,
        "baseline_at": "1970-01-01T00:00:00.000000Z",
    }


def create_schedule(
    *,
    bike_id: int | None = None,
    component_id: int | None = None,
    name: str | None = None,
    interval_miles: float | None = None,
    interval_days: int | None = None,
    service_type: str | None = None,
    interval_kind: str | None = None,
    interval_value: float | None = None,
    interval_unit: str | None = None,
    is_recurring: bool = True,
    notify: bool = True,
    today: date | None = None,
) -> MaintenanceSchedule:
    """Create a schedule: typed (service type + one interval, feature 040) or the older free-text form."""
    typed = service_type is not None
    if typed:
        if (bike_id is None) == (component_id is None):
            raise ValueError("A schedule must belong to exactly one of a bike or a component.")
        fields = _typed_fields(service_type, interval_kind, interval_value, interval_unit)
    else:
        _validate(
            bike_id=bike_id, component_id=component_id,
            interval_miles=interval_miles, interval_days=interval_days,
        )
        fields = {"name": name, "interval_miles": interval_miles, "interval_days": interval_days}
    with get_connection() as conn:
        owner = (
            bikes_db.get_by_id(conn, bike_id)
            if bike_id is not None
            else components_db.get_by_id(conn, component_id)
        )
        if owner is None:
            raise LookupError("No such bike or component to schedule maintenance for.")
        if typed:
            baseline = _baseline_for(
                conn, owner, bike_id=bike_id, component_id=component_id,
                service_type=service_type, today=_today(today),
            )
        else:
            baseline = {
                "baseline_mileage": owner.total_mileage,
                "baseline_date": _today(today).isoformat(),
                "baseline_at": _now_stored(),
            }
        return schedules_db.create(
            conn,
            bike_id=bike_id,
            component_id=component_id,
            is_recurring=is_recurring,
            notify=notify,
            **baseline,
            **fields,
        )


def form_defaults(schedule: MaintenanceSchedule | None) -> dict:
    """What the schedule form shows for a new schedule, a typed one, or one made before feature 040.

    An older schedule has no service type (the rider must choose one) and its interval is prefilled
    to review: miles as Usage/Miles, otherwise days as Period/Weeks (days / 7, at least 1).
    """
    if schedule is None:
        return {"service_type": "", "interval_kind": "usage", "interval_value": "", "interval_unit": "miles",
                "is_recurring": True, "notify": True, "older": False}
    common = {"is_recurring": schedule.is_recurring, "notify": schedule.notify}
    if schedule.service_type is not None:
        value = schedule.interval_value
        return {**common, "service_type": schedule.service_type, "interval_kind": schedule.interval_kind,
                "interval_value": f"{value:g}", "interval_unit": schedule.interval_unit, "older": False}
    if schedule.interval_miles is not None:
        return {**common, "service_type": "", "interval_kind": "usage",
                "interval_value": f"{schedule.interval_miles:g}", "interval_unit": "miles", "older": True}
    weeks = max(1, round((schedule.interval_days or 7) / 7))
    return {**common, "service_type": "", "interval_kind": "period", "interval_value": str(weeks),
            "interval_unit": "weeks", "older": True}


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
    name: str | None = None,
    interval_miles: float | None = None,
    interval_days: int | None = None,
    is_active: bool = True,
    service_type: str | None = None,
    interval_kind: str | None = None,
    interval_value: float | None = None,
    interval_unit: str | None = None,
    is_recurring: bool = True,
    notify: bool = True,
) -> MaintenanceSchedule:
    """Save a schedule. With `service_type` it is saved in the typed shape (this also converts an
    older schedule, keeping its cycle and baseline); otherwise as the older free-text form."""
    if service_type is not None:
        fields = _typed_fields(service_type, interval_kind, interval_value, interval_unit)
    elif interval_miles is None and interval_days is None:
        raise ValueError("A schedule needs a mileage interval, a time interval, or both.")
    with get_connection() as conn:
        if schedules_db.get_by_id(conn, schedule_id) is None:
            raise LookupError(f"No schedule with id {schedule_id}")
        if service_type is not None:
            return schedules_db.update_typed(
                conn, schedule_id, is_recurring=is_recurring, notify=notify, is_active=is_active, **fields
            )
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


def _usage(schedule: MaintenanceSchedule) -> tuple[str, float] | None:
    """(unit, interval) of the usage side of a schedule, older or typed; None for period-only."""
    if schedule.interval_kind == "usage":
        return schedule.interval_unit, schedule.interval_value
    if schedule.interval_kind is None and schedule.interval_miles is not None:
        return "miles", schedule.interval_miles
    return None


def _time_due(schedule: MaintenanceSchedule) -> date | None:
    """The date the period side of a schedule falls due, or None for usage-only."""
    baseline = date.fromisoformat(schedule.baseline_date)
    if schedule.interval_kind == "period":
        return add_period(baseline, int(schedule.interval_value), schedule.interval_unit)
    if schedule.interval_kind is None and schedule.interval_days is not None:
        return baseline + timedelta(days=schedule.interval_days)
    return None


def _used_since_baseline(conn, schedule: MaintenanceSchedule, unit: str) -> float:
    """Rides or hours since the schedule's last baseline (parts count only rides while installed)."""
    since = schedule.baseline_at or f"{schedule.baseline_date}T00:00:00.000000Z"
    rides, seconds = mileage_db.usage_since(
        conn, bike_id=schedule.bike_id, component_id=schedule.component_id, since=since
    )
    return float(rides) if unit == "rides" else seconds / 3600


def _trailing_usage_pace(conn, bike_id: int | None, today: date, unit: str) -> tuple[float, int]:
    """(rides or hours per day, distinct ride days) for a bike over the trailing window."""
    if bike_id is None:
        return 0.0, 0
    since = datetime.combine(
        today - timedelta(days=PACE_WINDOW_DAYS), datetime.min.time(), tzinfo=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    rides, seconds, ride_days = mileage_db.recent_usage_for_bike(conn, bike_id, since=since)
    amount = float(rides) if unit == "rides" else seconds / 3600
    return amount / PACE_WINDOW_DAYS, ride_days


def _with_latest_service(conn, schedule: MaintenanceSchedule) -> MaintenanceSchedule:
    """A typed schedule counts from its latest matching logged service when that is more recent
    than its saved starting point, however the entry got there (specs/046 FR-004)."""
    if schedule.service_type is None:
        return schedule
    entry = maintenance_db.latest_for_owner_and_type(
        conn, bike_id=schedule.bike_id, component_id=schedule.component_id, service_type=schedule.service_type
    )
    if entry is None:
        return schedule
    moment = maintenance_service.entry_moment(entry)
    if moment <= (schedule.baseline_at or f"{schedule.baseline_date}T00:00:00.000000Z"):
        return schedule
    return replace(
        schedule, baseline_mileage=entry.mileage_at_service, baseline_date=entry.performed_at, baseline_at=moment
    )


def _project(conn, schedule: MaintenanceSchedule, today: date) -> Projection:
    schedule = _with_latest_service(conn, schedule)
    owner = _owner(conn, schedule)
    current_mileage = owner.total_mileage if owner is not None else schedule.baseline_mileage

    time_due = _time_due(schedule)

    usage_due: date | None = None
    usage_trusted = False
    remaining: float | None = None
    unit: str | None = None
    usage_exceeded = False
    over: float | None = None
    usage = _usage(schedule)
    if usage is not None:
        unit, interval = usage
        if unit == "miles":
            remaining = schedule.baseline_mileage + interval - current_mileage
            pace, ride_days = _trailing_pace(conn, _top_bike_id(conn, schedule), today)
        else:
            remaining = interval - _used_since_baseline(conn, schedule, unit)
            pace, ride_days = _trailing_usage_pace(conn, _top_bike_id(conn, schedule), today, unit)
        if remaining <= 0:
            over = -remaining
            usage_exceeded = True
            usage_due = today
            usage_trusted = True  # already past the interval: no pace needed to know that
        elif pace > 0:
            usage_due = today + timedelta(days=math.ceil(remaining / pace - 1e-9))
            usage_trusted = ride_days >= MIN_RIDE_DAYS_FOR_CONFIDENCE
        remaining = max(remaining, 0.0)

    if usage_trusted:
        candidates = [d for d in (usage_due, time_due) if d is not None]
        due_at, low_confidence = min(candidates), False
    elif time_due is not None:
        # Not enough riding history to trust the usage side: time-only fallback (FR-018).
        due_at, low_confidence = time_due, False
    else:
        due_at, low_confidence = usage_due, True

    is_overdue = usage_exceeded or (time_due is not None and time_due < today)
    return Projection(
        due_at=due_at,
        remaining_miles=remaining if unit == "miles" else None,
        is_low_confidence=low_confidence,
        is_overdue=is_overdue,
        remaining=remaining,
        remaining_unit=unit,
        over=over,
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


REPEAT_COMPLETION_SECONDS = 5  # a second "Mark done" this soon is a double click, not a new job


def next_due_text(item: DueItem) -> str:
    """"Next due 2026-11-25" or, with only a usage interval, what it is waiting for."""
    if item.projection.due_at is not None:
        return f"Next due {item.projection.due_at.isoformat()}"
    usage = _usage(item.schedule)
    if usage:
        unit, interval = usage
        return f"Next due after {interval:.0f} more {unit}"
    return "Next due date not available yet"


def complete_schedule(schedule_id: int, *, today: date | None = None) -> MaintenanceSchedule:
    """Check off a schedule: log the maintenance and start the next cycle (FR-016).

    A repeat within `REPEAT_COMPLETION_SECONDS` of the previous completion (a double click) is
    ignored, so one burst of clicks logs one entry.
    """
    day = _today(today)
    with get_connection() as conn:
        schedule = schedules_db.get_by_id(conn, schedule_id)
        if schedule is None:
            raise LookupError(f"No schedule with id {schedule_id}")
        latest = maintenance_db.latest_for_schedule(conn, schedule_id)
    if latest is not None:
        logged = datetime.strptime(latest.created_at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        if (datetime.now(timezone.utc) - logged).total_seconds() < REPEAT_COMPLETION_SECONDS:
            return schedule

    entry = maintenance_service.log_maintenance(
        bike_id=schedule.bike_id,
        component_id=schedule.component_id,
        description=schedule.name,
        performed_at=day.isoformat(),
        schedule_id=schedule.id,
    )
    with get_connection() as conn:
        if not schedule.is_recurring:
            # One-time item: the maintenance is logged above; the schedule ends (specs/040 FR-006).
            schedules_db.deactivate(conn, schedule_id)
            ended = schedules_db.get_by_id(conn, schedule_id)
            assert ended is not None
            logger.info("completed one-time maintenance schedule schedule_id=%s name=%r", schedule_id, schedule.name)
            return ended
        completed = schedules_db.complete(
            conn,
            schedule_id,
            baseline_mileage=entry.mileage_at_service,
            baseline_date=day.isoformat(),
            baseline_at=_now_stored(),
        )
    logger.info(
        "completed maintenance schedule schedule_id=%s name=%r new_cycle=%s",
        schedule_id,
        schedule.name,
        completed.cycle_number,
    )
    return completed
