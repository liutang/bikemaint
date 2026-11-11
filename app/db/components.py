"""Parameterized query functions for `component` and `component_installation_period`.

Component nesting is a self-referential adjacency list (`parent_bike_id` /
`parent_component_id`); tree reads use `WITH RECURSIVE` per research.md §3.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import Component, ComponentInstallationPeriod


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def create(
    conn: sqlite3.Connection,
    *,
    name: str,
    component_type: str,
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
    manual_baseline_mileage: float = 0.0,
) -> Component:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO component (
            name, component_type, parent_bike_id, parent_component_id,
            manual_baseline_mileage, total_mileage, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            component_type,
            parent_bike_id,
            parent_component_id,
            manual_baseline_mileage,
            manual_baseline_mileage,
            now,
            now,
        ),
    )
    component = get_by_id(conn, cursor.lastrowid)
    assert component is not None
    return component


def get_by_id(conn: sqlite3.Connection, component_id: int) -> Component | None:
    row = conn.execute(
        "SELECT * FROM component WHERE id = ? AND is_deleted = 0", (component_id,)
    ).fetchone()
    return Component.from_row(row) if row else None


def list_children(
    conn: sqlite3.Connection,
    *,
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
) -> list[Component]:
    """Direct, non-deleted children of a bike, a component, or storage (both None)."""
    if parent_bike_id is not None:
        rows = conn.execute(
            "SELECT * FROM component WHERE parent_bike_id = ? AND is_deleted = 0 ORDER BY id",
            (parent_bike_id,),
        ).fetchall()
    elif parent_component_id is not None:
        rows = conn.execute(
            "SELECT * FROM component WHERE parent_component_id = ? AND is_deleted = 0 ORDER BY id",
            (parent_component_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM component
            WHERE parent_bike_id IS NULL AND parent_component_id IS NULL AND is_deleted = 0
            ORDER BY id
            """
        ).fetchall()
    return [Component.from_row(row) for row in rows]


def list_in_storage(conn: sqlite3.Connection) -> list[Component]:
    return list_children(conn, parent_bike_id=None, parent_component_id=None)


def get_descendants(conn: sqlite3.Connection, component_id: int) -> list[Component]:
    """Every non-deleted component nested (at any depth) under `component_id`, excluding it."""
    rows = conn.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM component WHERE parent_component_id = ? AND is_deleted = 0
            UNION ALL
            SELECT c.id FROM component c
            JOIN subtree s ON c.parent_component_id = s.id
            WHERE c.is_deleted = 0
        )
        SELECT component.* FROM component JOIN subtree ON component.id = subtree.id
        ORDER BY component.id
        """,
        (component_id,),
    ).fetchall()
    return [Component.from_row(row) for row in rows]


def get_tree_for_bike(conn: sqlite3.Connection, bike_id: int) -> list[Component]:
    """Every non-deleted component installed on `bike_id`, at any nesting depth."""
    rows = conn.execute(
        """
        WITH RECURSIVE tree(id) AS (
            SELECT id FROM component WHERE parent_bike_id = ? AND is_deleted = 0
            UNION ALL
            SELECT c.id FROM component c
            JOIN tree t ON c.parent_component_id = t.id
            WHERE c.is_deleted = 0
        )
        SELECT component.* FROM component JOIN tree ON component.id = tree.id
        ORDER BY component.id
        """,
        (bike_id,),
    ).fetchall()
    return [Component.from_row(row) for row in rows]


def update(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    name: str,
    component_type: str,
    manual_baseline_mileage: float,
    total_mileage: float,
) -> Component:
    conn.execute(
        """
        UPDATE component
        SET name = ?, component_type = ?, manual_baseline_mileage = ?, total_mileage = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (name, component_type, manual_baseline_mileage, total_mileage, _now(), component_id),
    )
    component = get_by_id(conn, component_id)
    assert component is not None
    return component


def set_parent(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    parent_bike_id: int | None,
    parent_component_id: int | None,
) -> Component:
    conn.execute(
        """
        UPDATE component
        SET parent_bike_id = ?, parent_component_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (parent_bike_id, parent_component_id, _now(), component_id),
    )
    component = get_by_id(conn, component_id)
    assert component is not None
    return component


def soft_delete(conn: sqlite3.Connection, component_id: int) -> None:
    conn.execute(
        "UPDATE component SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (_now(), component_id),
    )


def get_open_installation_period(
    conn: sqlite3.Connection, component_id: int
) -> ComponentInstallationPeriod | None:
    row = conn.execute(
        "SELECT * FROM component_installation_period WHERE component_id = ? AND removed_at IS NULL",
        (component_id,),
    ).fetchone()
    return ComponentInstallationPeriod.from_row(row) if row else None


def open_installation_period(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    parent_bike_id: int | None,
    parent_component_id: int | None,
    installed_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO component_installation_period (
            component_id, parent_bike_id, parent_component_id, installed_at
        ) VALUES (?, ?, ?, ?)
        """,
        (component_id, parent_bike_id, parent_component_id, installed_at),
    )


def close_open_installation_period(
    conn: sqlite3.Connection, component_id: int, *, removed_at: str
) -> None:
    conn.execute(
        """
        UPDATE component_installation_period
        SET removed_at = ?
        WHERE component_id = ? AND removed_at IS NULL
        """,
        (removed_at, component_id),
    )


def resolve_top_bike_id(conn: sqlite3.Connection, parent_component_id: int) -> int | None:
    """Walk up a chain of `parent_component_id`s to find the bike the chain terminates in.

    Returns None if the chain terminates in storage (a top-of-chain component with no
    bike) rather than a bike — e.g. a sub-assembly built up before being installed.
    """
    current_id: int | None = parent_component_id
    while current_id is not None:
        row = conn.execute(
            "SELECT parent_bike_id, parent_component_id FROM component WHERE id = ?",
            (current_id,),
        ).fetchone()
        if row is None:
            return None
        if row["parent_bike_id"] is not None:
            return row["parent_bike_id"]
        current_id = row["parent_component_id"]
    return None
