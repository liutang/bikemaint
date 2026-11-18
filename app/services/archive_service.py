"""Archiving bikes and parts (specs/079-archive-bikes-parts).

An item is locked when it is archived, or sits anywhere inside an archived bike or part
(research §1). A locked item allows only taking parts off to storage, deleting the archived item
itself, and unarchiving it. Every service that changes a bike or part asks `require_unlocked`
first, so the rule lives in one place.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Literal

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db.connection import get_connection

logger = logging.getLogger(__name__)

Kind = Literal["bike", "component"]


class ArchivedError(Exception):
    """A change was asked of a locked bike or part. The message says what is archived and what to do."""


@contextmanager
def _conn(conn: sqlite3.Connection | None):
    if conn is not None:
        yield conn
    else:
        with get_connection() as own:
            yield own


def _archived_holder(conn: sqlite3.Connection, component_id: int):
    """The archived thing that locks a part: ("component", part) or ("bike", bike), else None."""
    part = components_db.get_by_id(conn, component_id)
    seen = 0
    while part is not None and seen < 9:
        if part.archived_at is not None:
            return "component", part
        if part.parent_bike_id is not None:
            bike = bikes_db.get_by_id(conn, part.parent_bike_id)
            return ("bike", bike) if bike is not None and bike.archived_at is not None else None
        if part.parent_component_id is None:
            return None
        part = components_db.get_by_id(conn, part.parent_component_id)
        seen += 1
    return None


def is_locked(kind: Kind, item_id: int, conn: sqlite3.Connection | None = None) -> bool:
    """Whether the bike, or the part (itself, a part above it, or its bike), is archived."""
    with _conn(conn) as c:
        if kind == "bike":
            bike = bikes_db.get_by_id(c, item_id)
            return bike is not None and bike.archived_at is not None
        return components_db.is_in_archived_tree(c, item_id)


def require_unlocked(kind: Kind, item_id: int, conn: sqlite3.Connection | None = None) -> None:
    """Raise `ArchivedError` with the research §3 wording when the item is locked."""
    with _conn(conn) as c:
        if kind == "bike":
            bike = bikes_db.get_by_id(c, item_id)
            if bike is not None and bike.archived_at is not None:
                raise ArchivedError("This bike is archived. Unarchive it to change it.")
            return
        holder = _archived_holder(c, item_id)
    if holder is None:
        return
    holder_kind, holder_item = holder
    if holder_kind == "component" and holder_item.id == item_id:
        raise ArchivedError("This part is archived. Unarchive it to change it.")
    if holder_kind == "component":
        raise ArchivedError(
            f"This part is inside an archived part, {holder_item.name}. Take it off to storage, or unarchive that part."
        )
    raise ArchivedError(
        f"This part is on an archived bike, {holder_item.name}. Take it off to storage, or unarchive the bike."
    )


# ------------------------------------------------ archiving and unarchiving (research §4, §5)

Attached = Literal["keep", "move"]


def _now() -> str:
    from app.services import clock_service

    return clock_service.now()


def _turn_off_schedules(conn: sqlite3.Connection, *, bike_ids=(), component_ids=()) -> int:
    from app.db import schedules as schedules_db

    count = 0
    for bike_id in bike_ids:
        for schedule in schedules_db.list_active_for_bike(conn, bike_id):
            schedules_db.deactivate(conn, schedule.id)
            count += 1
    for component_id in component_ids:
        for schedule in schedules_db.list_active_for_component(conn, component_id):
            schedules_db.deactivate(conn, schedule.id)
            count += 1
    return count


def _settle(conn: sqlite3.Connection, attached: Attached | None, children, tree, now: str):
    """Apply the keep-or-move choice; returns (schedules turned off, parts moved)."""
    from app.services import component_service  # imported here: component_service will import this module

    if children and attached not in ("keep", "move"):
        raise ValueError("Choose whether to keep the parts on it or move them to storage.")
    if attached == "move":
        for child in children:
            component_service.detach_to_storage(conn, child.id, removed_at=now)
        return 0, len(children)
    return _turn_off_schedules(conn, component_ids=[p.id for p in tree]), 0


def archive_bike(bike_id: int, attached: Attached | None) -> None:
    """Archive a bike: settle its parts, turn off its schedules, unpair it, mark it archived (FR-002, FR-003)."""
    from app.db import mileage as mileage_db

    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            raise LookupError(f"No bike with id {bike_id}")
        require_unlocked("bike", bike_id, conn)
        now = _now()
        children = components_db.list_children(conn, parent_bike_id=bike_id)
        tree = components_db.get_tree_for_bike(conn, bike_id)
        off, moved = _settle(conn, attached, children, tree, now)
        off += _turn_off_schedules(conn, bike_ids=[bike_id])
        unpaired = bike.strava_gear_id is not None
        if unpaired:
            bikes_db.clear_strava_pairing(conn, bike_id)
        bikes_db.set_archived(conn, bike_id, now)
        mileage_db.recompute_all_component_totals(conn)
    logger.info(
        "bike archived bike_id=%s schedules_deleted=%s attached=%s parts_moved=%s unpaired=%s",
        bike_id, off, attached or "none", moved, "true" if unpaired else "false",
    )


def summary(kind: Kind, item_id: int) -> dict:
    """What archiving would do, for the Archive card's wording: counts of schedules and parts (US1 scenario 1)."""
    from app.db import schedules as schedules_db

    with get_connection() as conn:
        if kind == "bike":
            item = bikes_db.get_by_id(conn, item_id)
            own = schedules_db.list_active_for_bike(conn, item_id)
            tree = components_db.get_tree_for_bike(conn, item_id)
            paired = item is not None and item.strava_gear_id is not None
        else:
            own = schedules_db.list_active_for_component(conn, item_id)
            tree = components_db.get_descendants(conn, item_id)
            paired = False
        part_schedules = sum(len(schedules_db.list_active_for_component(conn, p.id)) for p in tree)
    return {"schedules": len(own), "parts": len(tree), "part_schedules": part_schedules, "paired": paired}
