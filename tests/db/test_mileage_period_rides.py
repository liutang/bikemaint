"""Rides that count toward one install period (specs/053-period-rides)."""

import pytest

from app.db import accounts, bikes, components, connection, mileage


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _world(conn):
    account = accounts.upsert_from_strava(
        conn, strava_athlete_id=1, access_token="a", refresh_token="r", expires_at="2099-01-01T00:00:00Z"
    )
    accounts.update_timezone(conn, account.id, "America/New_York")
    return bikes.create(conn, name="Madone"), components.create(conn, name="Chain", component_type="chain")


def _strava(conn, bike, n, miles, utc):
    mileage.upsert_ride_activity(
        conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles, occurred_at=utc
    )


def test_only_rides_on_that_bike_inside_the_period_in_order(db_path):
    with connection.get_connection() as conn:
        bike, part = _world(conn)
        other = bikes.create(conn, name="Gravel")
        _strava(conn, bike, 1, 22.1, "2024-08-22T16:41:10.000000Z")  # 12:41PM EDT: before the install
        _strava(conn, bike, 2, 25.7, "2024-08-24T12:32:00.000000Z")
        _strava(conn, bike, 3, 5.0, "2024-09-01T12:00:00.000000Z")
        _strava(conn, other, 4, 9.0, "2024-08-25T12:00:00.000000Z")  # other bike
        _strava(conn, bike, 5, 7.0, "2025-03-01T12:00:00.000000Z")  # after the removal
        period = components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at="2025-02-27T00:00:00.000000Z",
        )
        rides = mileage.list_rides_for_period(conn, period)

    assert [r.distance_miles for r in rides] == [25.7, 5.0]


def test_an_open_period_has_no_end_and_deleted_rides_are_left_out(db_path):
    with connection.get_connection() as conn:
        bike, part = _world(conn)
        _strava(conn, bike, 1, 10.0, "2024-09-01T12:00:00.000000Z")
        _strava(conn, bike, 2, 11.0, "2024-09-02T12:00:00.000000Z")
        conn.execute("UPDATE ride_activity SET deleted_by_user = 1 WHERE strava_activity_id = 2")
        period = components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at=None,
        )
        assert [r.distance_miles for r in mileage.list_rides_for_period(conn, period)] == [10.0]
