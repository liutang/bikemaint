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


def _next_position(
    conn: sqlite3.Connection, *, parent_bike_id: int | None, parent_component_id: int | None
) -> int:
    """One past the last live sibling under the given parent (storage when both are None)."""
    row = conn.execute(
        """
        SELECT COALESCE(MAX(position) + 1, 0) AS next FROM component
        WHERE parent_bike_id IS ? AND parent_component_id IS ? AND is_deleted = 0
        """,
        (parent_bike_id, parent_component_id),
    ).fetchone()
    return row["next"]


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
            manual_baseline_mileage, total_mileage, position, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            component_type,
            parent_bike_id,
            parent_component_id,
            manual_baseline_mileage,
            manual_baseline_mileage,
            _next_position(
                conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
            ),
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
            "SELECT * FROM component WHERE parent_bike_id = ? AND is_deleted = 0 ORDER BY position, id",
            (parent_bike_id,),
        ).fetchall()
    elif parent_component_id is not None:
        rows = conn.execute(
            "SELECT * FROM component WHERE parent_component_id = ? AND is_deleted = 0 ORDER BY position, id",
            (parent_component_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM component
            WHERE parent_bike_id IS NULL AND parent_component_id IS NULL AND is_deleted = 0
            ORDER BY position, id
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
        ORDER BY component.position, component.id
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
        ORDER BY component.position, component.id
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
        SET parent_bike_id = ?, parent_component_id = ?, position = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            parent_bike_id,
            parent_component_id,
            _next_position(
                conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
            ),
            _now(),
            component_id,
        ),
    )
    component = get_by_id(conn, component_id)
    assert component is not None
    return component


def reorder(
    conn: sqlite3.Connection, component_id: int, *, before_component_id: int | None
) -> None:
    """Place `component_id` just before a sibling (or last when None) and renumber 0..n.

    Both must live under the same parent; anything else raises ValueError.
    """
    component = get_by_id(conn, component_id)
    if component is None:
        raise LookupError(f"No component with id {component_id}")
    siblings = list_children(
        conn,
        parent_bike_id=component.parent_bike_id,
        parent_component_id=component.parent_component_id,
    )
    others = [c for c in siblings if c.id != component_id]
    if before_component_id is None:
        ordered = [*others, component]
    else:
        if before_component_id == component_id or all(c.id != before_component_id for c in others):
            raise ValueError("That position is not under the same parent.")
        ordered = []
        for sibling in others:
            if sibling.id == before_component_id:
                ordered.append(component)
            ordered.append(sibling)
    for index, item in enumerate(ordered):
        if item.position != index:
            conn.execute("UPDATE component SET position = ? WHERE id = ?", (index, item.id))


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


def list_periods(conn: sqlite3.Connection, component_id: int) -> list[ComponentInstallationPeriod]:
    """Every installation period of a component, oldest first."""
    rows = conn.execute(
        "SELECT * FROM component_installation_period WHERE component_id = ? "
        "ORDER BY installed_at, id",
        (component_id,),
    ).fetchall()
    return [ComponentInstallationPeriod.from_row(row) for row in rows]


def list_periods_for_bike(conn: sqlite3.Connection, bike_id: int) -> list[ComponentInstallationPeriod]:
    """Every installation period of every part that has been on `bike_id`, newest installed first.

    Periods record the top bike, so parts nested under other parts are included. Parts that were
    deleted later are included too: a history keeps what used to be there.
    """
    rows = conn.execute(
        "SELECT * FROM component_installation_period WHERE parent_bike_id = ? "
        "ORDER BY installed_at DESC, id DESC",
        (bike_id,),
    ).fetchall()
    return [ComponentInstallationPeriod.from_row(row) for row in rows]


def get_including_deleted(conn: sqlite3.Connection, component_id: int) -> Component | None:
    """A component whether or not it has since been deleted (for history screens)."""
    row = conn.execute("SELECT * FROM component WHERE id = ?", (component_id,)).fetchone()
    return Component.from_row(row) if row else None


def get_period(conn: sqlite3.Connection, period_id: int) -> ComponentInstallationPeriod | None:
    row = conn.execute(
        "SELECT * FROM component_installation_period WHERE id = ?", (period_id,)
    ).fetchone()
    return ComponentInstallationPeriod.from_row(row) if row else None


def insert_period(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    parent_bike_id: int | None,
    parent_component_id: int | None,
    installed_at: str,
    removed_at: str | None,
) -> ComponentInstallationPeriod:
    cursor = conn.execute(
        """
        INSERT INTO component_installation_period (
            component_id, parent_bike_id, parent_component_id, installed_at, removed_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (component_id, parent_bike_id, parent_component_id, installed_at, removed_at),
    )
    period = get_period(conn, cursor.lastrowid)
    assert period is not None
    return period


def update_period(
    conn: sqlite3.Connection,
    period_id: int,
    *,
    parent_bike_id: int | None,
    parent_component_id: int | None,
    installed_at: str,
    removed_at: str | None,
) -> ComponentInstallationPeriod:
    conn.execute(
        """
        UPDATE component_installation_period
        SET parent_bike_id = ?, parent_component_id = ?, installed_at = ?, removed_at = ?
        WHERE id = ?
        """,
        (parent_bike_id, parent_component_id, installed_at, removed_at, period_id),
    )
    period = get_period(conn, period_id)
    assert period is not None
    return period


def delete_period(conn: sqlite3.Connection, period_id: int) -> None:
    conn.execute("DELETE FROM component_installation_period WHERE id = ?", (period_id,))


def find_overlapping_period(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    installed_at: str,
    removed_at: str | None,
    exclude_period_id: int | None = None,
) -> ComponentInstallationPeriod | None:
    """A period of this component that overlaps [installed_at, removed_at) (None = open-ended).

    Periods that merely touch (one ends when the next starts) do not overlap.
    """
    row = conn.execute(
        """
        SELECT * FROM component_installation_period
        WHERE component_id = ?
          AND id != COALESCE(?, -1)
          AND installed_at < COALESCE(?, '9999-12-31T00:00:00.000000Z')
          AND COALESCE(removed_at, '9999-12-31T00:00:00.000000Z') > ?
        LIMIT 1
        """,
        (component_id, exclude_period_id, removed_at, installed_at),
    ).fetchone()
    return ComponentInstallationPeriod.from_row(row) if row else None
