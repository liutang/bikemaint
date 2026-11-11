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
from app.models.requests import BIKE_CATEGORIES
from app.services import sync_service
from app.services.component_service import ConfirmationRequiredError, detach_to_storage

__all__ = [
    "ConfirmationRequiredError",
    "create_bike",
    "create_bike_from_details",
    "update_bike_from_details",
    "get_bike",
    "list_bikes",
    "update_bike",
    "delete_bike",
    "pair_to_strava_gear",
    "unpaired_gear",
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


def _unique_name(conn, base: str, *, exclude_bike_id: int | None = None) -> str:
    taken = {b.name for b in bikes_db.list_active(conn) if b.id != exclude_bike_id}
    if base not in taken:
        return base
    number = 2
    while f"{base} ({number})" in taken:
        number += 1
    return f"{base} ({number})"


def _check_category(category: str) -> None:
    if category not in BIKE_CATEGORIES:
        raise ValueError("Choose a category from the list.")


def create_bike_from_details(
    *, year: int, make: str, model: str, category: str, manual_baseline_mileage: float = 0.0
) -> Bike:
    """Add a bike by year, make, model and category; its name is "Year Make Model"."""
    _check_category(category)
    with get_connection() as conn:
        return bikes_db.create(
            conn,
            name=_unique_name(conn, f"{year} {make} {model}"),
            bike_type=category,
            manual_baseline_mileage=manual_baseline_mileage,
            year=year,
            make=make,
            model=model,
        )


def update_bike_from_details(
    bike_id: int,
    *,
    year: int | None,
    make: str | None,
    model: str | None,
    category: str,
    manual_baseline_mileage: float,
) -> Bike:
    """Edit a bike. A bike with a single legacy name may leave year, make and model all blank to
    keep that name; any other mix of blank and filled details is refused."""
    _check_category(category)
    given = [bool(year), bool(make), bool(model)]
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        legacy = bike.year is None and bike.make is None and bike.model is None
        if not any(given):
            if not legacy:
                raise ValueError("Enter the year, make and model.")
            name, year, make, model = bike.name, None, None, None
        elif not all(given):
            raise ValueError("Enter the year, make and model, or leave all three blank to keep the name.")
        else:
            wanted = f"{year} {make} {model}"
            same = (bike.year, bike.make, bike.model) == (year, make, model)
            name = bike.name if same else _unique_name(conn, wanted, exclude_bike_id=bike_id)
        earned_beyond_baseline = bike.total_mileage - bike.manual_baseline_mileage
        return bikes_db.update(
            conn,
            bike_id,
            name=name,
            bike_type=category,
            manual_baseline_mileage=manual_baseline_mileage,
            total_mileage=earned_beyond_baseline + manual_baseline_mileage,
            year=year,
            make=make,
            model=model,
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


def unpaired_gear(gear: list[dict]) -> list[dict]:
    """`gear` minus entries already paired to one of the garage's bikes."""
    paired_ids = {bike.strava_gear_id for bike in list_bikes() if bike.strava_gear_id}
    return [entry for entry in gear if entry["id"] not in paired_ids]


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
    """Delete a bike. Its parts are kept: they move to storage with their own sub-trees."""
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        top_level_components = components_db.list_children(conn, parent_bike_id=bike_id)
        if top_level_components and not confirmed:
            raise ConfirmationRequiredError(
                "Its parts will move to storage; confirm to delete the bike."
            )
        has_history_or_schedule = maintenance_db.has_entries_for_bike(
            conn, bike_id
        ) or schedules_db.has_active_for_bike(conn, bike_id)
        if has_history_or_schedule and not confirmed:
            raise ConfirmationRequiredError(
                "It has maintenance history or an active schedule; confirm to delete it."
            )
        now = _now()
        for component in top_level_components:
            detach_to_storage(conn, component.id, removed_at=now)
        bikes_db.soft_delete(conn, bike_id)
