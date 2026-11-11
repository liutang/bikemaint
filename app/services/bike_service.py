"""Business logic for bikes: creation, edits, and confirmation-gated soft-delete (FR-020).

Per Constitution Principle II this module is callable without FastAPI/request objects;
`app/routers/bikes.py` only translates HTTP concerns to/from these functions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import maintenance as maintenance_db
from app.db import schedules as schedules_db
from app.db.connection import get_connection
from app.models.rows import Bike
from app.services import sync_service
from app.services.component_service import ConfirmationRequiredError, soft_delete_recursive

__all__ = [
    "ConfirmationRequiredError",
    "create_bike",
    "get_bike",
    "list_bikes",
    "update_bike",
    "delete_bike",
    "pair_to_strava_gear",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_bike(bike_id: int) -> Bike | None:
    with get_connection() as conn:
        return bikes_db.get_by_id(conn, bike_id)


def list_bikes() -> list[Bike]:
    with get_connection() as conn:
        return bikes_db.list_active(conn)


def create_bike(
    *, name: str, bike_type: str | None = None, manual_baseline_mileage: float = 0.0
) -> Bike:
    with get_connection() as conn:
        return bikes_db.create(
            conn, name=name, bike_type=bike_type, manual_baseline_mileage=manual_baseline_mileage
        )


def update_bike(
    bike_id: int, *, name: str, bike_type: str | None, manual_baseline_mileage: float
) -> Bike:
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        mileage_earned_beyond_baseline = bike.total_mileage - bike.manual_baseline_mileage
        new_total_mileage = mileage_earned_beyond_baseline + manual_baseline_mileage
        return bikes_db.update(
            conn,
            bike_id,
            name=name,
            bike_type=bike_type,
            manual_baseline_mileage=manual_baseline_mileage,
            total_mileage=new_total_mileage,
        )


def pair_to_strava_gear(bike_id: int, strava_gear_id: str) -> Bike:
    """Pair `bike_id` to a Strava gear entry and import its full ride history (FR-022)."""
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        bikes_db.set_strava_pairing(
            conn, bike_id, strava_gear_id=strava_gear_id, strava_paired_at=_now()
        )
    sync_service.backfill_bike(bike_id)
    updated = get_bike(bike_id)
    assert updated is not None
    return updated


def delete_bike(bike_id: int, *, confirmed: bool = False) -> None:
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        top_level_components = components_db.list_children(conn, parent_bike_id=bike_id)
        if top_level_components and not confirmed:
            raise ConfirmationRequiredError(
                "This bike has installed components; confirm to delete them too."
            )
        has_history_or_schedule = (
            maintenance_db.has_entries_for_bike(conn, bike_id)
            or schedules_db.has_active_for_bike(conn, bike_id)
            or any(
                maintenance_db.has_entries_for_component(conn, c.id)
                or schedules_db.has_active_for_component(conn, c.id)
                for top in top_level_components
                for c in [top, *components_db.get_descendants(conn, top.id)]
            )
        )
        if has_history_or_schedule and not confirmed:
            raise ConfirmationRequiredError(
                "This bike (or something installed on it) has maintenance history or an "
                "active schedule; confirm to delete it."
            )
        now = _now()
        for component in top_level_components:
            soft_delete_recursive(conn, component.id, removed_at=now)
        bikes_db.soft_delete(conn, bike_id)
