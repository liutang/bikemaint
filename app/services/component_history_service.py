"""Install dates and the manual parts history (specs/015-component-install-history).

A part's mileage comes from the rides on each bike it was installed on, between install and
removal. This module lets the rider state those moments (at add time and by back-filling past
periods) and keeps the totals right. Callable without FastAPI (Constitution Principle II).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db.connection import get_connection
from app.models.rows import ComponentInstallationPeriod

_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_moment() -> str:
    return datetime.now(timezone.utc).strftime(_FORMAT)


def moment(day: str | None, time: str | None) -> str:
    """Build a stored timestamp from typed date/time; both blank means now.

    A date alone counts as 00:00; a time without a date is an error. Stored as typed (no zone
    conversion), like rides.
    """
    if not day:
        if time:
            raise ValueError("Enter a date with the time.")
        return now_moment()
    try:
        datetime.strptime(day, "%Y-%m-%d")
        if time:
            datetime.strptime(time, "%H:%M")
    except ValueError as exc:
        raise ValueError("Enter a valid date and time.") from exc
    return f"{day}T{time or '00:00'}:00.000000Z"


def check_not_future(value: str, label: str = "The install time") -> None:
    if value > now_moment():
        raise ValueError(f"{label} cannot be in the future.")


def recompute(component_id: int) -> float:
    with get_connection() as conn:
        return mileage_db.recompute_component_total_mileage(conn, component_id)


def list_history(component_id: int) -> list[ComponentInstallationPeriod]:
    with get_connection() as conn:
        return components_db.list_periods(conn, component_id)


def get_period(period_id: int) -> ComponentInstallationPeriod | None:
    with get_connection() as conn:
        return components_db.get_period(conn, period_id)


def place_name(conn: sqlite3.Connection, period: ComponentInstallationPeriod) -> str:
    """Where the part was: its parent part's name, else the bike's, else 'a bike (deleted)'."""
    if period.parent_component_id is not None:
        parent = components_db.get_by_id(conn, period.parent_component_id)
        if parent is not None:
            return parent.name
    if period.parent_bike_id is not None:
        bike = bikes_db.get_by_id(conn, period.parent_bike_id)
        if bike is not None:
            return bike.name
    return "Storage"


def describe_history(component_id: int) -> list[dict]:
    """Periods with a place label and the miles ridden in each (for the history screen)."""
    with get_connection() as conn:
        rows = []
        for period in components_db.list_periods(conn, component_id):
            miles = conn.execute(
                """
                SELECT COALESCE(SUM(distance_miles), 0) AS total FROM ride_activity
                WHERE bike_id = ? AND occurred_at >= ? AND (? IS NULL OR occurred_at < ?)
                  AND is_deleted_upstream = 0 AND deleted_by_user = 0
                """,
                (period.parent_bike_id, period.installed_at, period.removed_at, period.removed_at),
            ).fetchone()["total"]
            rows.append({"period": period, "place": place_name(conn, period), "miles": miles})
        return rows


def _validate(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    bike_id: int,
    parent_component_id: int | None,
    installed_at: str,
    removed_at: str | None,
    exclude_period_id: int | None,
    open_period: bool,
) -> None:
    if components_db.get_by_id(conn, component_id) is None:
        raise LookupError(f"No component with id {component_id}")
    if bikes_db.get_by_id(conn, bike_id) is None:
        raise LookupError(f"No bike with id {bike_id}")
    if parent_component_id is not None:
        if parent_component_id == component_id:
            raise ValueError("A part cannot be installed inside itself.")
        if components_db.get_by_id(conn, parent_component_id) is None:
            raise LookupError(f"No component with id {parent_component_id}")
    check_not_future(installed_at)
    if removed_at is None and not open_period:
        raise ValueError("Enter a removal date, or install the part instead if it is still installed.")
    if removed_at is not None:
        if removed_at <= installed_at:
            raise ValueError("The removal time must be after the install time.")
        check_not_future(removed_at, "The removal time")
    clash = components_db.find_overlapping_period(
        conn, component_id, installed_at=installed_at, removed_at=removed_at,
        exclude_period_id=exclude_period_id,
    )
    if clash is not None:
        raise ValueError(
            f"That overlaps another period ({clash.installed_at[:10]} to "
            f"{clash.removed_at[:10] if clash.removed_at else 'now'}) for this part."
        )


def log_period(
    component_id: int,
    *,
    bike_id: int,
    installed_at: str,
    removed_at: str | None,
    parent_component_id: int | None = None,
) -> ComponentInstallationPeriod:
    """Add a past period (installed on a bike, optionally under a part there, then removed)."""
    with get_connection() as conn:
        _validate(
            conn, component_id, bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at, exclude_period_id=None,
            open_period=False,
        )
        period = components_db.insert_period(
            conn, component_id, parent_bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at,
        )
        mileage_db.recompute_component_total_mileage(conn, component_id)
        return period


def update_period(
    period_id: int,
    *,
    bike_id: int,
    installed_at: str,
    removed_at: str | None,
    parent_component_id: int | None = None,
) -> ComponentInstallationPeriod:
    """Edit a period. A still-installed (open) period keeps no removal time."""
    with get_connection() as conn:
        existing = components_db.get_period(conn, period_id)
        if existing is None:
            raise LookupError(f"No installation period with id {period_id}")
        is_open = existing.removed_at is None
        if is_open and removed_at is not None:
            raise ValueError("This part is still installed; remove it from the bike to end this period.")
        _validate(
            conn, existing.component_id, bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at, exclude_period_id=period_id,
            open_period=is_open,
        )
        period = components_db.update_period(
            conn, period_id, parent_bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at,
        )
        mileage_db.recompute_component_total_mileage(conn, existing.component_id)
        return period


def delete_period(period_id: int) -> None:
    """Remove a closed period. The part's live (open) period cannot be deleted by hand."""
    with get_connection() as conn:
        existing = components_db.get_period(conn, period_id)
        if existing is None:
            raise LookupError(f"No installation period with id {period_id}")
        if existing.removed_at is None:
            raise ValueError("This part is still installed; remove it from the bike instead.")
        components_db.delete_period(conn, period_id)
        mileage_db.recompute_component_total_mileage(conn, existing.component_id)
