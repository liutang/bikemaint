"""Business logic for the maintenance log (User Story 3).

Per Constitution Principle II this module is callable without FastAPI/request objects;
`app/routers/maintenance.py` only translates HTTP concerns to/from these functions.
Entries belong to a bike or a component by id, so a component's history stays with it
when it moves between bikes (Acceptance Scenario US3-2).
"""

from __future__ import annotations

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import maintenance as maintenance_db
from app.db.connection import get_connection
from app.models.rows import MaintenanceLogEntry


def get_entry(entry_id: int) -> MaintenanceLogEntry | None:
    with get_connection() as conn:
        return maintenance_db.get_by_id(conn, entry_id)


def list_for_bike(bike_id: int) -> list[MaintenanceLogEntry]:
    with get_connection() as conn:
        return maintenance_db.list_for_bike(conn, bike_id)


def list_for_component(component_id: int) -> list[MaintenanceLogEntry]:
    with get_connection() as conn:
        return maintenance_db.list_for_component(conn, component_id)


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
    """Record completed maintenance; `mileage_at_service` defaults to the item's current total."""
    if (bike_id is None) == (component_id is None):
        raise ValueError("Maintenance must be logged against exactly one of a bike or a component.")
    with get_connection() as conn:
        if bike_id is not None:
            bike = bikes_db.get_by_id(conn, bike_id)
            if bike is None:
                raise LookupError(f"No bike with id {bike_id}")
            current_mileage = bike.total_mileage
        else:
            component = components_db.get_by_id(conn, component_id)
            if component is None:
                raise LookupError(f"No component with id {component_id}")
            current_mileage = component.total_mileage
        return maintenance_db.create(
            conn,
            bike_id=bike_id,
            component_id=component_id,
            description=description,
            performed_at=performed_at,
            mileage_at_service=current_mileage if mileage_at_service is None else mileage_at_service,
            schedule_id=schedule_id,
            performed_time=performed_time,
        )


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
        return maintenance_db.update(
            conn,
            entry_id,
            description=description,
            performed_at=performed_at,
            mileage_at_service=mileage_at_service,
            performed_time=performed_time,
        )


def delete_entry(entry_id: int) -> None:
    with get_connection() as conn:
        if maintenance_db.get_by_id(conn, entry_id) is None:
            raise LookupError(f"No maintenance entry with id {entry_id}")
        maintenance_db.delete(conn, entry_id)
