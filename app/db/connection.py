"""SQLite connection helper and migration runner.

No ORM per the constitution's fixed technology stack — this module is the sole
place `sqlite3` is configured (foreign keys, row factory, `DATABASE_PATH`).
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from app.db import frames, typed_times

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Python data steps, run once each after the `.sql` migrations and recorded in `schema_version`
# under their name like a migration file (specs/075 research §6). Each runs in one transaction
# with its record, so a failure leaves nothing changed and the step runs again at the next start.
# (name, step, copy_first): copy_first saves a copy of the database beside it before the step,
# when there is anything to change (specs/075 research §7). The 076 repair changes only broken
# values and makes no copy (specs/076 Assumptions).
DATA_STEPS: list[tuple[str, Callable[[sqlite3.Connection], dict[str, int]], bool]] = [
    ("0019_typed_times_utc", typed_times.convert_database, True),
    ("0020_four_digit_years", typed_times.repair_database, False),
]


def _database_path() -> str:
    return os.environ["DATABASE_PATH"]


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    frames.register(conn)
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


def _copy_path() -> Path:
    """Where the pre-update copy goes: beside the database, named with today's date (specs/075)."""
    path = Path(_database_path())
    day = datetime.now(timezone.utc).date().isoformat()
    return path.with_name(f"{path.stem}-before-075-{day}{path.suffix}")


def _copy_database(conn: sqlite3.Connection) -> None:
    """Save a whole copy of the database before converting; refuse to go on if that fails."""
    target = _copy_path()
    try:
        copy = sqlite3.connect(target)
        try:
            conn.backup(copy)
        finally:
            copy.close()
    except (sqlite3.Error, OSError) as exc:
        logger.error("could not save the pre-update copy path=%s error=%s; nothing was converted", target, exc)
        raise RuntimeError(f"Could not save a copy of the database to {target}; nothing was converted.") from exc
    logger.info("saved a copy of the database before converting typed times path=%s", target)


def _run_data_steps(conn: sqlite3.Connection, applied: set[str]) -> None:
    for name, step, copy_first in DATA_STEPS:
        if name in applied:
            continue
        if copy_first and _database_path() != ":memory:" and typed_times.has_rows(conn):
            _copy_database(conn)
        counts = step(conn)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (name,))
        conn.commit()
        logger.info(
            "data step done step=%s %s", name, " ".join(f"{table}={n}" for table, n in counts.items())
        )


def run_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> None:
    """Apply every pending `*.sql` file in `migrations_dir`, in filename order, exactly once,
    then every pending data step (`DATA_STEPS`)."""
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
        conn.commit()
        if migrations_dir == MIGRATIONS_DIR:  # a partial folder (tests of older schemas) has no data steps
            _run_data_steps(conn, applied)
