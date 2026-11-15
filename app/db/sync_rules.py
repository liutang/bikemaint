"""Sync rule storage (specs/060-sync-rules): one rule per bike or per part."""

from __future__ import annotations

import sqlite3

from app.models.sync_rules import SyncRule


def _where(bike_id: int | None, component_id: int | None) -> tuple[str, int]:
    return ("bike_id", bike_id) if bike_id is not None else ("component_id", component_id)


def get(conn: sqlite3.Connection, *, bike_id: int | None = None, component_id: int | None = None) -> SyncRule | None:
    column, owner = _where(bike_id, component_id)
    row = conn.execute(
        f"SELECT sports, ride_types, keywords FROM sync_rule WHERE {column} = ?", (owner,)
    ).fetchone()
    return SyncRule(row["sports"], row["ride_types"], row["keywords"]) if row else None


def save(
    conn: sqlite3.Connection, rule: SyncRule, *, bike_id: int | None = None, component_id: int | None = None
) -> None:
    """Store the rule, or remove it when it filters nothing."""
    column, owner = _where(bike_id, component_id)
    conn.execute(f"DELETE FROM sync_rule WHERE {column} = ?", (owner,))
    if not rule.is_empty:
        conn.execute(
            f"INSERT INTO sync_rule ({column}, sports, ride_types, keywords) VALUES (?, ?, ?, ?)",
            (owner, rule.sports, rule.ride_types, rule.keywords),
        )
