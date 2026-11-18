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

    A date alone counts as 00:00; a time without a date is an error. Read in the saved zone and
    stored in UTC, like rides (specs/075).
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
    return clock_service.to_utc(day, time or "00:00")


def check_not_future(value: str, label: str = "The install time") -> None:
    """Every stored moment is a UTC instant, so compare with the current instant."""
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


def default_bike_id(component_id: int) -> int | None:
    """The bike to preselect when logging a period (specs/058): where the part is installed now
    (through its parent parts), else the bike of its most recent period, if that bike still exists."""
    with get_connection() as conn:
        part = components_db.get_by_id(conn, component_id)
        if part is None:
            return None
        bike_id = part.parent_bike_id
        if bike_id is None and part.parent_component_id is not None:
            bike_id = components_db.resolve_top_bike_id(conn, part.parent_component_id)
        if bike_id is None:
            periods = sorted(components_db.list_periods(conn, component_id), key=lambda p: (p.installed_at, p.id))
            bike_id = periods[-1].parent_bike_id if periods else None
        return bike_id if bike_id is not None and bikes_db.get_by_id(conn, bike_id) is not None else None


def parent_options(component_id: int, current_parent_id: int | None = None) -> list[dict]:
    """The "Inside part" choices for a period of `component_id` (specs/063).

    None first, then every live part except itself as "Name (Kind)" (a " #id" suffix only where
    two entries would read the same), then the period's current parent when it has been deleted.
    """
    from app.models.component_kinds import kind_name

    with get_connection() as conn:
        parts = [p for p in components_db.list_active(conn) if p.id != component_id]
        current = components_db.get_including_deleted(conn, current_parent_id) if current_parent_id else None
    labels = [f"{p.name} ({kind_name(p.component_type)})" for p in parts]
    options = [{"value": "", "label": "None (on the bike or frame)"}]
    for part, label in zip(parts, labels):
        options.append({"value": str(part.id), "label": f"{label} #{part.id}" if labels.count(label) > 1 else label})
    if current is not None and current.is_deleted:
        options.append({"value": str(current.id), "label": f"{current.name} ({kind_name(current.component_type)}) (deleted)"})
    return options


def describe_history(component_id: int) -> list[dict]:
    """Periods, latest installed first, with a place label and the miles ridden in each."""
    with get_connection() as conn:
        rows = []
        # Latest installed first (specs/035); ties: newest entry first.
        for period in reversed(components_db.list_periods(conn, component_id)):
            miles = sum(r.distance_miles for r in mileage_db.list_rides_for_period(conn, period))
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
            f"That overlaps another period ({clock_service.to_local(clash.installed_at)[:10]} to "
            f"{clock_service.to_local(clash.removed_at)[:10] if clash.removed_at else 'now'}) for this part."
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
                conn, component_id, parent_bike_id=None if parent_component_id is not None else bike_id,
                parent_component_id=parent_component_id, installed_at=installed_at, removed_at=removed_at,
            )
            mileage_db.recompute_all_component_totals(conn)  # parts inside it may earn from it (specs/064)
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
    removal moment it stays installed: the install moment changes, and a new place moves the part
    there as of that moment, with its sub-parts (015 FR-014).
    """
    with get_connection() as conn:
        existing = components_db.get_period(conn, period_id)
        if existing is None:
            raise LookupError(f"No installation period with id {period_id}")
        # An unchanged date and minute keep the stored instant, seconds included (specs/075 FR-003).
        installed_at = clock_service.keep_if_same(existing.installed_at, installed_at)
        removed_at = clock_service.keep_if_same(existing.removed_at, removed_at)
        is_open = existing.removed_at is None
        ending = is_open and removed_at is not None
        _validate(
            conn, existing.component_id, bike_id=bike_id, parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=removed_at, exclude_period_id=period_id,
            open_period=is_open and not ending,
        )
        if is_open and not ending:
            period = _place_open_period(
                conn, existing, bike_id=bike_id, parent_component_id=parent_component_id, installed_at=installed_at,
            )
            mileage_db.recompute_all_component_totals(conn)
            return period
        period = components_db.update_period(
            conn, period_id, parent_bike_id=None if parent_component_id is not None and not is_open else bike_id,
            parent_component_id=parent_component_id,
            installed_at=installed_at, removed_at=None if ending else removed_at,
        )
        if not ending:
            mileage_db.recompute_all_component_totals(conn)
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


def _place_open_period(
    conn: sqlite3.Connection,
    existing: ComponentInstallationPeriod,
    *,
    bike_id: int,
    parent_component_id: int | None,
    installed_at: str,
) -> ComponentInstallationPeriod:
    """Save a still-installed period and put the part where it says (015 FR-014, branch 078).

    The part moves as of the period's install moment, so no new period is added. The bike recorded
    is the one the part is really on: the chosen bike, or the bike the chosen Inside part is on
    (none if that part is in storage). Parts inside it keep their own install moments and follow
    it to that bike.
    """
    component_id = existing.component_id
    if parent_component_id is not None:
        inside = {d.id for d in components_db.get_descendants(conn, component_id)}
        if parent_component_id in inside:
            raise ValueError("A component cannot be moved into its own installed sub-tree.")
        top_bike_id = components_db.resolve_top_bike_id(conn, parent_component_id)
    else:
        top_bike_id = bike_id
    part = components_db.get_by_id(conn, component_id)
    new_place = (None if parent_component_id is not None else bike_id, parent_component_id)
    moved = part is not None and (part.parent_bike_id, part.parent_component_id) != new_place
    if moved:
        components_db.set_parent(conn, component_id, parent_bike_id=new_place[0], parent_component_id=new_place[1])
    period = components_db.update_period(
        conn, existing.id, parent_bike_id=top_bike_id, parent_component_id=parent_component_id,
        installed_at=installed_at, removed_at=None,
    )
    for descendant in components_db.get_descendants(conn, component_id):
        components_db.set_open_period_bike(conn, descendant.id, parent_bike_id=top_bike_id)
    if moved:
        logger.info(
            "part moved by period edit component_id=%s period_id=%s bike_id=%s parent_component_id=%s",
            component_id, existing.id, top_bike_id, parent_component_id,
        )
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
        mileage_db.recompute_all_component_totals(conn)
