"""Ride log for bikes and parts (specs/006-feedback-round-2, M3).

A bike's mileage is its starting (baseline) mileage plus its live rides plus any manual
adjustments. Rides come from Strava or are added by hand; the rider can edit, re-assign and
delete any of them, and Strava sync never undoes those changes. Every change recomputes the
mileage of the bikes involved and of every part that has ever been installed on them.

Per Constitution Principle II this module is callable without FastAPI/request objects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db.connection import get_connection
from app.models.rows import RideActivity

logger = logging.getLogger(__name__)

MAX_RIDE_MILES = 5000.0


@dataclass(frozen=True)
class RideRow:
    kind: str  # "start" | "ride" | "adjustment"
    id: int | None
    occurred_at: str | None
    miles: float
    running_total: float
    source: str | None = None  # "strava" | "manual" for rides
    note: str | None = None
    editable: bool = False
    bike_name: str | None = None  # which bike a part's ride was on
    moving_seconds: int | None = None


@dataclass(frozen=True)
class RideLog:
    owner_kind: str  # "bike" | "component"
    owner_id: int
    owner_name: str
    rows: list[RideRow]  # newest first, then the start row last
    total: float


def parse_duration(text: str | None) -> int | None:
    """`h:mm` to seconds; blank is None (the request model has already validated the shape)."""
    if not text or not text.strip():
        return None
    hours, minutes = text.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60


def format_duration(seconds: int | None) -> str:
    """Seconds as `h:mm` (whole minutes); blank when unknown."""
    if not seconds:
        return ""
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}"


def _occurred_at(day: date, time: str | None) -> str:
    """Stored as typed (no zone conversion); a ride without a time counts as noon."""
    return f"{day.isoformat()}T{time or '12:00'}:00.000000Z"


def _check_miles(miles: float) -> None:
    if not 0 < miles <= MAX_RIDE_MILES:
        raise ValueError(f"Miles must be more than 0 and at most {MAX_RIDE_MILES:.0f}.")


def _recompute(conn, bike_ids: set[int]) -> None:
    for bike_id in bike_ids:
        mileage_db.recompute_bike_total_mileage(conn, bike_id)
    for component_id in mileage_db.component_ids_with_history_on(conn, bike_ids):
        mileage_db.recompute_component_total_mileage(conn, component_id)


def _require_bike(conn, bike_id: int):
    bike = bikes_db.get_by_id(conn, bike_id)
    if bike is None:
        raise LookupError(f"No bike with id {bike_id}")
    return bike


def _build_rows(
    baseline: float,
    rides: list[tuple[RideActivity, str | None]],
    adjustments: list,
    *,
    editable: bool,
) -> tuple[list[RideRow], float]:
    """Running totals are computed oldest to newest; the log is shown newest first."""
    events = [(r.occurred_at, 0, r.id, "ride", r, bike) for r, bike in rides]
    events += [(a.created_at, 1, a.id, "adjustment", a, None) for a in adjustments]
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    total = baseline
    built: list[RideRow] = []
    for when, _, entry_id, kind, entry, bike_name in events:
        if kind == "ride":
            total += entry.distance_miles
            built.append(
                RideRow("ride", entry_id, when, entry.distance_miles, total, source=entry.source,
                        note=entry.note, editable=editable, bike_name=bike_name,
                        moving_seconds=entry.moving_time_seconds)
            )
        else:
            total += entry.delta_miles
            built.append(RideRow("adjustment", entry_id, when, entry.delta_miles, total, note=entry.reason))
    built.reverse()
    return [*built, RideRow("start", None, None, baseline, baseline)], total


def get_log_for_bike(bike_id: int) -> RideLog:
    with get_connection() as conn:
        bike = _require_bike(conn, bike_id)
        rides = [(r, None) for r in mileage_db.list_rides_for_bike(conn, bike_id)]
        adjustments = mileage_db.list_adjustments(conn, bike_id=bike_id)
        rows, total = _build_rows(bike.manual_baseline_mileage, rides, adjustments, editable=True)
    return RideLog("bike", bike.id, bike.name, rows, total)


def get_log_for_component(component_id: int) -> RideLog:
    """Read-only: the rides during which the part was installed on a bike."""
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")
        names: dict[int, str] = {}
        rides = []
        for ride in mileage_db.list_rides_for_component(conn, component_id):
            if ride.bike_id not in names:
                bike = bikes_db.get_by_id(conn, ride.bike_id)
                names[ride.bike_id] = bike.name if bike else "Bike"
            rides.append((ride, names[ride.bike_id]))
        adjustments = mileage_db.list_adjustments(conn, component_id=component_id)
        rows, total = _build_rows(component.manual_baseline_mileage, rides, adjustments, editable=False)
    return RideLog("component", component.id, component.name, rows, total)


def get_ride(ride_id: int) -> RideActivity | None:
    with get_connection() as conn:
        ride = mileage_db.get_ride(conn, ride_id)
    return None if ride is None or ride.deleted_by_user else ride


def create_ride(
    bike_id: int, *, day: date, time: str | None, miles: float, note: str | None,
    moving_seconds: int | None = None,
) -> RideActivity:
    """Add a ride that is not tracked on Strava."""
    _check_miles(miles)
    with get_connection() as conn:
        _require_bike(conn, bike_id)
        ride = mileage_db.create_manual_ride(
            conn, bike_id=bike_id, distance_miles=miles, occurred_at=_occurred_at(day, time), note=note,
            moving_time_seconds=moving_seconds,
        )
        _recompute(conn, {bike_id})
    logger.info("ride added ride_id=%s bike_id=%s miles=%s source=manual", ride.id, bike_id, miles)
    return ride


def update_ride(
    ride_id: int, *, bike_id: int, day: date, time: str | None, miles: float, note: str | None,
    moving_seconds: int | None = None,
) -> RideActivity:
    """Edit a ride's miles, time, note, or re-assign it to another bike."""
    _check_miles(miles)
    with get_connection() as conn:
        existing = mileage_db.get_ride(conn, ride_id)
        if existing is None or existing.deleted_by_user:
            raise LookupError(f"No ride with id {ride_id}")
        _require_bike(conn, bike_id)
        ride = mileage_db.update_ride(
            conn, ride_id, bike_id=bike_id, distance_miles=miles,
            occurred_at=_occurred_at(day, time), note=note, moving_time_seconds=moving_seconds,
        )
        affected = {bike_id} | ({existing.bike_id} if existing.bike_id is not None else set())
        _recompute(conn, affected)
    logger.info("ride edited ride_id=%s bike_id=%s miles=%s", ride_id, bike_id, miles)
    return ride


def delete_ride(ride_id: int) -> None:
    with get_connection() as conn:
        existing = mileage_db.get_ride(conn, ride_id)
        if existing is None or existing.deleted_by_user:
            raise LookupError(f"No ride with id {ride_id}")
        mileage_db.delete_ride(conn, ride_id)
        if existing.bike_id is not None:
            _recompute(conn, {existing.bike_id})
    logger.info("ride deleted ride_id=%s bike_id=%s", ride_id, existing.bike_id)
