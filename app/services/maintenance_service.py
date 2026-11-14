"""Business logic for the maintenance log (User Story 3).

Per Constitution Principle II this module is callable without FastAPI/request objects;
`app/routers/maintenance.py` only translates HTTP concerns to/from these functions.
Entries belong to a bike or a component by id, so a component's history stays with it
when it moves between bikes (Acceptance Scenario US3-2).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import maintenance as maintenance_db
from app.db import mileage as mileage_db
from app.db import schedules as schedules_db
from app.db.connection import get_connection
from app.models.rows import MaintenanceLogEntry


def get_entry(entry_id: int) -> MaintenanceLogEntry | None:
    with get_connection() as conn:
        return maintenance_db.get_by_id(conn, entry_id)


def list_for_bike(bike_id: int) -> list[MaintenanceLogEntry]:
    with get_connection() as conn:
        return maintenance_db.list_for_bike(conn, bike_id)


@dataclass(frozen=True)
class HistoryRow:
    """One line of a maintenance history: the entry and which part it belongs to (specs/048)."""

    entry: MaintenanceLogEntry
    part_id: int | None  # None on a bike's history
    part_name: str | None
    is_own: bool  # the entry belongs to the screen's own part or bike (editable there)


def _sort_key(row: HistoryRow):
    entry = row.entry
    return (entry.performed_at, entry.performed_time or entry.created_at[11:16], entry.id)


def list_for_bike_rows(bike_id: int) -> list[HistoryRow]:
    return [HistoryRow(e, None, None, True) for e in list_for_bike(bike_id)]


def list_for_component_tree(component_id: int) -> list[HistoryRow]:
    """A part's own entries plus those of every part currently attached to it, latest first."""
    with get_connection() as conn:
        part = components_db.get_by_id(conn, component_id)
        if part is None:
            raise LookupError(f"No component with id {component_id}")
        parts = [(part, True)] + [(p, False) for p in components_db.get_descendants(conn, component_id)]
        rows = [
            HistoryRow(entry, p.id, p.name, own)
            for p, own in parts
            for entry in maintenance_db.list_for_component(conn, p.id)
        ]
    return sorted(rows, key=_sort_key, reverse=True)


def list_for_component(component_id: int) -> list[MaintenanceLogEntry]:
    with get_connection() as conn:
        return maintenance_db.list_for_component(conn, component_id)


def entry_moment(entry: MaintenanceLogEntry) -> str:
    """When an entry was performed, in the stored format (a blank time counts the whole day)."""
    if entry.performed_time:
        return f"{entry.performed_at}T{entry.performed_time}:00.000000Z"
    return f"{entry.performed_at}T23:59:59.999999Z"


def _rebase_matching_schedules(conn, entry: MaintenanceLogEntry, *, new_cycle: bool) -> None:
    """Restart counting for this owner's active schedules of the entry's service type (specs/046).

    Only schedules whose current starting point is earlier than the entry move; a new cycle lets
    due-soon notifications fire again.
    """
    schedules = (
        schedules_db.list_active_for_bike(conn, entry.bike_id)
        if entry.bike_id is not None
        else schedules_db.list_active_for_component(conn, entry.component_id)
    )
    moment = entry_moment(entry)
    for schedule in schedules:
        if schedule.service_type != entry.description:
            continue
        if moment <= (schedule.baseline_at or f"{schedule.baseline_date}T00:00:00.000000Z"):
            continue
        args = dict(baseline_mileage=entry.mileage_at_service, baseline_date=entry.performed_at)
        if new_cycle:
            schedules_db.complete(conn, schedule.id, baseline_at=moment, **args)
        else:
            schedules_db.rebase(conn, schedule.id, baseline_at=moment, **args)


def log_maintenance(
    *,
    bike_id: int | None = None,
    component_id: int | None = None,
    description: str,
    performed_at: str,
    mileage_at_service: float | None = None,
    schedule_id: int | None = None,
    performed_time: str | None = None,
) -> MaintenanceLogEntry:
    """Record completed maintenance.

    A blank `mileage_at_service` is the item's mileage as of the date and time performed (a blank
    time counts the whole day), worked out from its ride history (specs/038).
    """
    if (bike_id is None) == (component_id is None):
        raise ValueError("Maintenance must be logged against exactly one of a bike or a component.")
    at = f"{performed_at}T{performed_time or '23:59:59'}.999999Z"
    with get_connection() as conn:
        if bike_id is not None:
            bike = bikes_db.get_by_id(conn, bike_id)
            if bike is None:
                raise LookupError(f"No bike with id {bike_id}")
            mileage_then = lambda conn: mileage_db.bike_mileage_at(conn, bike_id, at)  # noqa: E731
        else:
            component = components_db.get_by_id(conn, component_id)
            if component is None:
                raise LookupError(f"No component with id {component_id}")
            mileage_then = lambda conn: mileage_db.component_mileage_at(conn, component_id, at)  # noqa: E731
        entry = maintenance_db.create(
            conn,
            bike_id=bike_id,
            component_id=component_id,
            description=description,
            performed_at=performed_at,
            mileage_at_service=mileage_then(conn) if mileage_at_service is None else mileage_at_service,
            schedule_id=schedule_id,
            performed_time=performed_time,
        )
        if schedule_id is None:  # a schedule's own completion restarts itself
            _rebase_matching_schedules(conn, entry, new_cycle=True)
        return entry


def update_entry(
    entry_id: int,
    *,
    description: str,
    performed_at: str,
    mileage_at_service: float,
    performed_time: str | None = None,
) -> MaintenanceLogEntry:
    with get_connection() as conn:
        if maintenance_db.get_by_id(conn, entry_id) is None:
            raise LookupError(f"No maintenance entry with id {entry_id}")
        entry = maintenance_db.update(
            conn,
            entry_id,
            description=description,
            performed_at=performed_at,
            mileage_at_service=mileage_at_service,
            performed_time=performed_time,
        )
        _rebase_matching_schedules(conn, entry, new_cycle=False)
        return entry


def delete_entry(entry_id: int) -> None:
    with get_connection() as conn:
        if maintenance_db.get_by_id(conn, entry_id) is None:
            raise LookupError(f"No maintenance entry with id {entry_id}")
        maintenance_db.delete(conn, entry_id)
