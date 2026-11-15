"""Sync rules: which Strava rides count for a bike or part (specs/060-sync-rules).

Callable without FastAPI (Constitution Principle II).
"""

from __future__ import annotations

import logging

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import mileage as mileage_db
from app.db import sync_rules as rules_db
from app.db.connection import get_connection
from app.models import sync_rules as model
from app.models.sync_rules import SyncRule

logger = logging.getLogger(__name__)


def get_rule(kind: str, owner_id: int) -> SyncRule:
    """The saved rule, or an empty one (which filters nothing)."""
    with get_connection() as conn:
        found = rules_db.get(conn, **{f"{kind}_id": owner_id})
    return found or SyncRule()


def apply_to_bike(conn, bike_id: int) -> None:
    """Re-check a bike's Strava rides against its rule, then recompute its and its parts' mileage."""
    mileage_db.apply_bike_rule(conn, bike_id, rules_db.get(conn, bike_id=bike_id))
    mileage_db.recompute_bike_total_mileage(conn, bike_id)
    for component_id in mileage_db.component_ids_with_history_on(conn, {bike_id}):
        mileage_db.recompute_component_total_mileage(conn, component_id)


def validate_rule(sports: list[str], ride_types: list[str], keywords: str) -> SyncRule:
    """The cleaned rule for the submitted choices; ValueError when something is not allowed."""
    return SyncRule(
        model.clean_choices(sports, model.SPORTS),
        model.clean_choices(ride_types, model.RIDE_TYPES),
        model.clean_keywords(keywords),
    )


def save_rule(kind: str, owner_id: int, *, sports: list[str], ride_types: list[str], keywords: str) -> SyncRule:
    """Validate and save a bike's or part's rule and re-apply it to every existing ride."""
    rule = validate_rule(sports, ride_types, keywords)
    with get_connection() as conn:
        exists = bikes_db.get_by_id(conn, owner_id) if kind == "bike" else components_db.get_by_id(conn, owner_id)
        if exists is None:
            raise LookupError(f"No {kind} with id {owner_id}")
        rules_db.save(conn, rule, **{f"{kind}_id": owner_id})
        if kind == "bike":
            apply_to_bike(conn, owner_id)
        else:
            mileage_db.recompute_component_total_mileage(conn, owner_id)
    logger.info("sync rule saved kind=%s id=%s sports=%s types=%s keywords=%s", kind, owner_id, rule.sports, rule.ride_types, rule.keywords)
    return rule
