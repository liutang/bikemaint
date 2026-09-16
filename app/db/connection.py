"""SQLite connection helper and migration runner.

No ORM per the constitution's fixed technology stack — this module is the sole
place `sqlite3` is configured (foreign keys, row factory, `DATABASE_PATH`).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _database_path() -> str:
    return os.environ["DATABASE_PATH"]


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_version").fetchall()
    return {row["version"] for row in rows}


def run_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> None:
    """Apply every pending `*.sql` file in `migrations_dir`, in filename order, exactly once."""
    with get_connection() as conn:
        _ensure_schema_version_table(conn)
        applied = _applied_versions(conn)
        pending = sorted(
            path for path in migrations_dir.glob("*.sql") if path.name not in applied
        )
        for migration in pending:
            conn.executescript(migration.read_text())
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (migration.name,)
            )
