"""Rides and hours since a moment, and the recent pace (specs/040)."""

import pytest

from app.db import bikes, components, connection, mileage


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as c:
        yield c


def _ride(conn, bike_id, n, when, secs, miles=10):
    mileage.upsert_ride_activity(
        conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike_id, distance_miles=miles,
        occurred_at=when, moving_time_seconds=secs,
    )


def test_a_bike_counts_rides_and_seconds_after_the_moment(conn):
    bike = bikes.create(conn, name="Road")
    _ride(conn, bike.id, 1, "2026-03-01T08:00:00.000000Z", 3600)
    _ride(conn, bike.id, 2, "2026-04-01T08:00:00.000000Z", 1800)
    _ride(conn, bike.id, 3, "2026-05-01T08:00:00.000000Z", None)

    assert mileage.usage_since(conn, bike_id=bike.id, since="2026-03-15T00:00:00.000000Z") == (2, 1800)
    assert mileage.usage_since(conn, bike_id=bike.id, since="2026-01-01T00:00:00.000000Z") == (3, 5400)


def test_deleted_rides_do_not_count(conn):
    bike = bikes.create(conn, name="Road")
    _ride(conn, bike.id, 1, "2026-03-01T08:00:00.000000Z", 3600)
    conn.execute("UPDATE ride_activity SET deleted_by_user = 1")

    assert mileage.usage_since(conn, bike_id=bike.id, since="2026-01-01T00:00:00.000000Z") == (0, 0)


def test_recent_usage_is_rides_seconds_and_ride_days(conn):
    bike = bikes.create(conn, name="Road")
    _ride(conn, bike.id, 1, "2026-03-01T08:00:00.000000Z", 3600)
    _ride(conn, bike.id, 2, "2026-03-01T18:00:00.000000Z", 600)
    _ride(conn, bike.id, 3, "2026-03-05T08:00:00.000000Z", 600)

    assert mileage.recent_usage_for_bike(conn, bike.id, since="2026-01-01T00:00:00.000000Z") == (3, 4800, 2)
