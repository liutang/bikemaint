"""Tests for the not-yet-implemented `app/db/mileage.py` (User Story 2).

Written ahead of the implementation per the constitution's TDD mandate
(Principle III) — expect these to fail (missing module/table) until
T035/T036 land.
"""

import pytest

from app.db import connection, mileage


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_upsert_ride_activity_is_idempotent_on_strava_activity_id(db_path):
    with connection.get_connection() as conn:
        mileage.upsert_ride_activity(
            conn,
            strava_activity_id=555,
            strava_gear_id="gear-1",
            bike_id=None,
            distance_miles=10.0,
            occurred_at="2026-09-01T08:00:00.000000Z",
        )
        mileage.upsert_ride_activity(
            conn,
            strava_activity_id=555,
            strava_gear_id="gear-1",
            bike_id=None,
            distance_miles=10.0,
            occurred_at="2026-09-01T08:00:00.000000Z",
        )
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM ride_activity WHERE strava_activity_id = 555"
        ).fetchone()["c"]

    assert count == 1


def test_upsert_ride_activity_updates_distance_on_re_sync(db_path):
    with connection.get_connection() as conn:
        mileage.upsert_ride_activity(
            conn,
            strava_activity_id=777,
            strava_gear_id="gear-1",
            bike_id=None,
            distance_miles=10.0,
            occurred_at="2026-09-01T08:00:00.000000Z",
        )
        # Simulates Strava reporting a corrected distance for the same activity.
        mileage.upsert_ride_activity(
            conn,
            strava_activity_id=777,
            strava_gear_id="gear-1",
            bike_id=None,
            distance_miles=12.5,
            occurred_at="2026-09-01T08:00:00.000000Z",
        )
        row = conn.execute(
            "SELECT distance_miles FROM ride_activity WHERE strava_activity_id = 777"
        ).fetchone()

    assert row["distance_miles"] == pytest.approx(12.5)
