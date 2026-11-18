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


def test_strava_never_moves_or_changes_a_ride_of_an_archived_bike(tmp_path, monkeypatch):
    """specs/079 FR-010: re-importing the same gear onto another bike leaves archived rides alone."""
    from app.db import bikes as bikes_db, connection, mileage

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        old = bikes_db.create(conn, name="Old")
        new = bikes_db.create(conn, name="New")
        kw = dict(strava_gear_id="g", occurred_at="2026-09-01T08:00:00.000000Z")
        mileage.upsert_ride_activity(conn, strava_activity_id=1, bike_id=old.id, distance_miles=10.0, **kw)
        mileage.upsert_ride_activity(conn, strava_activity_id=2, bike_id=new.id, distance_miles=10.0, **kw)
        bikes_db.set_archived(conn, old.id, "2026-11-18T00:00:00.000000Z")

        mileage.upsert_ride_activity(conn, strava_activity_id=1, bike_id=new.id, distance_miles=99.0, **kw)
        mileage.upsert_ride_activity(conn, strava_activity_id=2, bike_id=new.id, distance_miles=20.0, **kw)

        rows = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT strava_activity_id, bike_id, distance_miles FROM ride_activity")}
    assert rows == {1: (old.id, 10.0), 2: (new.id, 20.0)}
