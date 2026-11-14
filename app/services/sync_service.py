"""Business logic for Strava activity sync and mileage attribution (User Story 2).

Per Constitution Principle II this module is callable without FastAPI/request objects;
`app/routers/mileage.py` only translates HTTP concerns to/from these functions.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from app.db import accounts as accounts_db
from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db.connection import get_connection
from app.models.rows import Bike, Component
from app.services import strava_client

logger = logging.getLogger(__name__)

METERS_PER_MILE = 1609.34


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _meters_to_miles(meters: float) -> float:
    return meters / METERS_PER_MILE


def _normalize_strava_timestamp(value: str) -> str:
    """Strava's `start_date` is `YYYY-MM-DDTHH:MM:SSZ`; normalize to our stored format."""
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _moving_seconds(activity: dict) -> int | None:
    """Strava's moving time in whole seconds, or None when it is absent or zero."""
    value = activity.get("moving_time")
    return int(value) if isinstance(value, (int, float)) and value > 0 else None


def _upsert_activities(conn: sqlite3.Connection, activities: list[dict]) -> set[int]:
    """Upsert `activities`, resolving each to a bike via its Strava gear id.

    Returns the set of bike ids touched, so the caller knows which bikes/components'
    `total_mileage` needs recomputing.
    """
    touched_bike_ids: set[int] = set()
    for activity in activities:
        gear_id = activity.get("gear_id")
        bike = bikes_db.get_by_strava_gear_id(conn, gear_id) if gear_id else None
        mileage_db.upsert_ride_activity(
            conn,
            strava_activity_id=activity["id"],
            strava_gear_id=gear_id,
            bike_id=bike.id if bike else None,
            distance_miles=_meters_to_miles(activity["distance"]),
            occurred_at=_normalize_strava_timestamp(activity["start_date"]),
            moving_time_seconds=_moving_seconds(activity),
        )
        if bike is not None:
            touched_bike_ids.add(bike.id)
    return touched_bike_ids


def _recompute_bike_and_its_components(conn: sqlite3.Connection, bike_id: int) -> None:
    mileage_db.recompute_bike_total_mileage(conn, bike_id)
    for component in components_db.get_tree_for_bike(conn, bike_id):
        mileage_db.recompute_component_total_mileage(conn, component.id)


def sync_incremental(account_id: int) -> None:
    """Fetch and attribute activity recorded since the last sync (research.md §7).

    Same code path the scheduled job and the manual `POST /sync/strava` route use.
    """
    with get_connection() as conn:
        account = accounts_db.get_by_id(conn, account_id)
        if account is None:
            raise LookupError(f"No account with id {account_id}")
        after = mileage_db.latest_ride_epoch(conn)

    try:
        access_token = strava_client.ensure_fresh_access_token(account)
    except strava_client.StravaTokenRefreshError:
        # Acceptance Scenario US2-3: flag is already set; skip without losing prior data.
        logger.warning(
            "skipping Strava sync: token refresh failed, connection marked stale account_id=%s",
            account_id,
        )
        return

    activities = strava_client.get_activities(access_token, after=after)

    with get_connection() as conn:
        touched_bike_ids = _upsert_activities(conn, activities)
        for bike_id in touched_bike_ids:
            _recompute_bike_and_its_components(conn, bike_id)
        accounts_db.mark_synced(conn, account_id)
    logger.info(
        "Strava incremental sync finished account_id=%s activities=%s bikes_updated=%s",
        account_id,
        len(activities),
        len(touched_bike_ids),
    )


def backfill_bike(bike_id: int) -> None:
    """One-time full-history import triggered when a bike is newly paired (FR-022)."""
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        account = accounts_db.get_singleton(conn)
        if account is None:
            raise LookupError("No connected Strava account")

    access_token = strava_client.ensure_fresh_access_token(account)
    activities = strava_client.get_activities(access_token)

    with get_connection() as conn:
        _upsert_activities(conn, activities)
        _recompute_bike_and_its_components(conn, bike_id)
        accounts_db.mark_synced(conn, account.id)
    logger.info(
        "Strava backfill finished bike_id=%s activities_fetched=%s", bike_id, len(activities)
    )


def adjust_bike_mileage(bike_id: int, *, delta_miles: float, reason: str | None = None) -> Bike:
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        mileage_db.insert_mileage_adjustment(
            conn, bike_id=bike_id, component_id=None, delta_miles=delta_miles, reason=reason
        )
        mileage_db.recompute_bike_total_mileage(conn, bike_id)
        updated = bikes_db.get_by_id(conn, bike_id)
        assert updated is not None
        return updated


def adjust_component_mileage(
    component_id: int, *, delta_miles: float, reason: str | None = None
) -> Component:
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")
        mileage_db.insert_mileage_adjustment(
            conn, bike_id=None, component_id=component_id, delta_miles=delta_miles, reason=reason
        )
        mileage_db.recompute_component_total_mileage(conn, component_id)
        updated = components_db.get_by_id(conn, component_id)
        assert updated is not None
        return updated
