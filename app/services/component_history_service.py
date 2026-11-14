"""Install dates and the manual parts history (specs/015-component-install-history).

A part's mileage comes from the rides on each bike it was installed on, between install and
removal. This module lets the rider state those moments (at add time and by back-filling past
periods) and keeps the totals right. Callable without FastAPI (Constitution Principle II).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.models.component_kinds import kind_name
from app.services import clock_service
from app.db import mileage as mileage_db
from app.db.connection import get_connection
from app.models.rows import ComponentInstallationPeriod

logger = logging.getLogger(__name__)

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
    """Typed moments are wall-clock times, so compare with the current time in the rider's zone."""
    if value > clock_service.now_in_zone_moment():
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


def place(conn: sqlite3.Connection, period: ComponentInstallationPeriod) -> tuple[str, str | None]:
    """Where the part was and a link to it if it still exists (specs/031-screen-polish).

    The parent part's name (linked to its screen), else the bike's (linked to its screen); plain
    text for a deleted part or bike, or Storage.
    """
    if period.parent_component_id is not None:
        parent = components_db.get_by_id(conn, period.parent_component_id)
        if parent is not None:
            return parent.name, f"/components/{parent.id}"
        return "a deleted part", None
    if period.parent_bike_id is not None:
        bike = bikes_db.get_by_id(conn, period.parent_bike_id)
        if bike is not None:
            return bike.name, f"/bikes/{bike.id}"
        return "a bike (deleted)", None
    return "Storage", None


def place_name(conn: sqlite3.Connection, period: ComponentInstallationPeriod) -> str:
    """Where the part was: its parent part's name, else the bike's, else 'Storage'."""
    return place(conn, period)[0]


def describe_history(component_id: int) -> list[dict]:
    """Periods, latest installed first, with a place label and the miles ridden in each."""
    with get_connection() as conn:
        rows = []
        # Latest installed first (specs/035); ties: newest entry first.
        for period in reversed(components_db.list_periods(conn, component_id)):
            miles = conn.execute(
                """
                SELECT COALESCE(SUM(distance_miles), 0) AS total FROM ride_activity
                WHERE bike_id = ? AND ride_wall(occurred_at, source) >= period_wall(?)
                  AND (? IS NULL OR ride_wall(occurred_at, source) < period_wall(?))
                  AND is_deleted_upstream = 0 AND deleted_by_user = 0
                """,
                (period.parent_bike_id, period.installed_at, period.removed_at, period.removed_at),
            ).fetchone()["total"]
            name, url = place(conn, period)
            rows.append({"period": period, "place": name, "place_url": url, "miles": miles})
        return rows


def describe_bike_history(bike_id: int) -> list[dict]:
    """Every part that has been on a bike, newest installed first (specs/022).

    Each row: the period, the part (even if deleted since), its kind's display name, where it was
    placed, and whether the part still exists to link to.
    """
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        rows = []
        for period in components_db.list_periods_for_bike(conn, bike_id):
            part = components_db.get_including_deleted(conn, period.component_id)
            if part is None:
                continue
            if period.parent_component_id is not None:
                parent = components_db.get_including_deleted(conn, period.parent_component_id)
                if parent is None or parent.is_deleted:
                    place_text, url = "a deleted part", None
                else:
                    place_text, url = parent.name, f"/components/{parent.id}"
            else:
                place_text, url = (bike.name, f"/bikes/{bike.id}") if bike is not None else ("the bike", None)
            rows.append(
                {
                    "period": period,
                    "component": part,
                    "kind_name": kind_name(part.component_type),
                    "place": place_text,
                    "place_url": url,
                    "linked": not part.is_deleted,
                }
            )
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
    """Add a period: installed on a bike (optionally under a part there), then removed or not.

    With no removal moment the part is installed now: it moves onto the bike (or into the part)
    as of `installed_at` and gets a current period (specs/022 FR-012). The part must be in storage
    and the moment must not overlap another of its periods.
    """
    still_installed = removed_at is None
    with get_connection() as conn:
        _validate(
            conn, component_id, bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at, exclude_period_id=None,
            open_period=still_installed,
        )
        if not still_installed:
            period = components_db.insert_period(
                conn, component_id, parent_bike_id=bike_id, parent_component_id=parent_component_id,
                installed_at=installed_at, removed_at=removed_at,
            )
            mileage_db.recompute_component_total_mileage(conn, component_id)
            return period
    # The move opens its own connection, so it runs after validation's connection is closed.
    from app.services import component_service  # imported here: component_service imports this module

    component_service.move_component(
        component_id,
        parent_bike_id=None if parent_component_id is not None else bike_id,
        parent_component_id=parent_component_id,
        moved_at=installed_at,
    )
    with get_connection() as conn:
        mileage_db.recompute_component_total_mileage(conn, component_id)
        for descendant in components_db.get_descendants(conn, component_id):
            mileage_db.recompute_component_total_mileage(conn, descendant.id)
        period = components_db.list_periods(conn, component_id)[-1]
    logger.info("part installed by log component_id=%s installed_at=%s", component_id, installed_at)
    return period


def update_period(
    period_id: int,
    *,
    bike_id: int,
    installed_at: str,
    removed_at: str | None,
    parent_component_id: int | None = None,
) -> ComponentInstallationPeriod:
    """Edit a period.

    A still-installed (open) period given a removal moment is ended: the part is moved to storage
    at that moment (with its sub-parts) and its mileage is recalculated (specs/030). With no
    removal moment it stays installed and only the install moment and place change.
    """
    with get_connection() as conn:
        existing = components_db.get_period(conn, period_id)
        if existing is None:
            raise LookupError(f"No installation period with id {period_id}")
        is_open = existing.removed_at is None
        ending = is_open and removed_at is not None
        _validate(
            conn, existing.component_id, bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at, exclude_period_id=period_id,
            open_period=is_open and not ending,
        )
        period = components_db.update_period(
            conn, period_id, parent_bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=None if ending else removed_at,
        )
        if not ending:
            mileage_db.recompute_component_total_mileage(conn, existing.component_id)
            return period
    # The move opens its own connection, so it runs after the edit above is saved.
    from app.services import component_service  # imported here: component_service imports this module

    component_service.move_component(existing.component_id, moved_at=removed_at)
    with get_connection() as conn:
        mileage_db.recompute_component_total_mileage(conn, existing.component_id)
        for descendant in components_db.get_descendants(conn, existing.component_id):
            mileage_db.recompute_component_total_mileage(conn, descendant.id)
        ended = components_db.get_period(conn, period_id)
    logger.info(
        "installation ended by edit component_id=%s period_id=%s removed_at=%s",
        existing.component_id, period_id, removed_at,
    )
    return ended


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
