"""Migration 0015 rebuilds maintenance_schedule for the new interval kinds (specs/040)."""

import shutil
import sqlite3

import pytest

from app.db import connection
from app.db.connection import MIGRATIONS_DIR


def _older(tmp_path):
    older = tmp_path / "migrations"
    older.mkdir()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name < "0015":
            shutil.copy(path, older / path.name)
    return older


def test_old_schedules_and_their_notifications_survive_the_rebuild(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations(_older(tmp_path))
    with connection.get_connection() as conn:
        conn.execute("INSERT INTO bike (name, bike_type, created_at, updated_at) VALUES ('B', 'road', 'x', 'x')")
        conn.execute(
            "INSERT INTO maintenance_schedule (bike_id, name, interval_miles, interval_days, baseline_mileage,"
            " baseline_date, cycle_number, created_at, updated_at) VALUES (1, 'Lube chain', 200, 30, 5, '2026-01-01', 3, 'x', 'x')"
        )
        conn.execute(
            "INSERT INTO notification (schedule_id, cycle_number, projected_due_at, created_at)"
            " VALUES (1, 3, '2026-02-01', 'x')"
        )

    connection.run_migrations()  # applies 0015

    with connection.get_connection() as conn:
        row = conn.execute("SELECT * FROM maintenance_schedule WHERE id = 1").fetchone()
        assert (row["name"], row["interval_miles"], row["interval_days"], row["cycle_number"]) == ("Lube chain", 200, 30, 3)
        assert (row["service_type"], row["interval_kind"], row["is_recurring"], row["notify"]) == (None, None, 1, 1)
        assert conn.execute("SELECT schedule_id FROM notification").fetchone()["schedule_id"] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_a_rides_schedule_with_no_mileage_or_day_interval_is_allowed_but_an_empty_one_is_not(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        conn.execute("INSERT INTO bike (name, bike_type, created_at, updated_at) VALUES ('B', 'road', 'x', 'x')")
        conn.execute(
            "INSERT INTO maintenance_schedule (bike_id, name, interval_kind, interval_value, interval_unit,"
            " baseline_mileage, baseline_date, created_at, updated_at)"
            " VALUES (1, 'Check', 'usage', 50, 'rides', 0, '2026-01-01', 'x', 'x')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO maintenance_schedule (bike_id, name, baseline_mileage, baseline_date, created_at, updated_at)"
                " VALUES (1, 'Nothing', 0, '2026-01-01', 'x', 'x')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO maintenance_schedule (bike_id, name, interval_kind, interval_value, interval_unit,"
                " baseline_mileage, baseline_date, created_at, updated_at)"
                " VALUES (1, 'Bad', 'usage', 5, 'parsecs', 0, '2026-01-01', 'x', 'x')"
            )
