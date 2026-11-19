"""Migration 0023 moves manual rides' notes into their titles (specs/083)."""

import shutil

from app.db import connection
from app.db.connection import MIGRATIONS_DIR


def _older(tmp_path):
    older = tmp_path / "migrations"
    older.mkdir()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name < "0023":
            shutil.copy(path, older / path.name)
    return older


def test_manual_notes_become_titles_and_strava_rides_are_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations(_older(tmp_path))
    with connection.get_connection() as conn:
        conn.execute("INSERT INTO bike (name, created_at, updated_at) VALUES ('B', 'x', 'x')")
        ride = "INSERT INTO ride_activity (source, strava_activity_id, bike_id, distance_miles, occurred_at, note, activity_name, user_modified) VALUES (?, ?, 1, 5, '2026-01-01T12:00:00.000000Z', ?, ?, ?)"
        conn.execute(ride, ("manual", None, "Trainer", None, 1))
        conn.execute(ride, ("manual", None, None, None, 1))
        conn.execute(ride, ("manual", None, "  ", None, 1))
        conn.execute(ride, ("strava", 7, "Chain skipped", "Morning Ride", 0))

    connection.run_migrations()

    with connection.get_connection() as conn:
        rows = [tuple(r) for r in conn.execute("SELECT source, activity_name, note FROM ride_activity ORDER BY id")]
    assert rows == [
        ("manual", "Trainer", None),
        ("manual", "Manual Ride", None),
        ("manual", "Manual Ride", None),
        ("strava", "Morning Ride", "Chain skipped"),
    ]
