"""Install periods and rides are compared in one clock (specs/015 FR-013, branch 051).

Strava rides are stored as UTC instants; times the rider types for a period are wall-clock times
in the saved zone. A period starting 12:51PM EDT must not include a ride that started 12:41PM EDT
(stored as 16:41 UTC).
"""

import pytest

from app.db import accounts, bikes, components, connection, mileage


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _setup(conn, zone="America/New_York"):
    account = accounts.upsert_from_strava(
        conn, strava_athlete_id=1, access_token="a", refresh_token="r", expires_at="2099-01-01T00:00:00Z"
    )
    accounts.update_timezone(conn, account.id, zone)
    bike = bikes.create(conn, name="Madone")
    part = components.create(conn, name="Chain", component_type="chain")
    return bike, part


def _strava(conn, bike, n, miles, utc):
    mileage.upsert_ride_activity(
        conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id,
        distance_miles=miles, occurred_at=utc,
    )


def test_ride_before_a_typed_install_time_is_excluded(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        _strava(conn, bike, 1, 22.1, "2024-08-22T16:41:10.000000Z")  # 12:41PM EDT, before install
        _strava(conn, bike, 2, 25.7, "2024-08-24T12:32:00.000000Z")  # 8:32AM EDT on the 24th
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z",   # typed: 12:51PM
            removed_at="2025-02-27T00:00:00.000000Z",     # typed: midnight
        )
        total = mileage.recompute_component_total_mileage(conn, part.id)
        listed = [r.distance_miles for r in mileage.list_rides_for_component(conn, part.id)]

    assert total == 25.7
    assert listed == [25.7]


def test_ride_after_a_typed_install_time_is_included(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        _strava(conn, bike, 1, 10.0, "2024-08-22T17:05:00.000000Z")  # 1:05PM EDT, after 12:51PM
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at=None,
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 10.0


def test_a_ride_late_on_the_removal_day_is_excluded_after_a_midnight_removal(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        _strava(conn, bike, 1, 15.8, "2025-02-27T04:30:00.000000Z")  # 11:30PM EST on the 26th
        _strava(conn, bike, 2, 5.0, "2025-02-27T05:30:00.000000Z")   # 12:30AM EST on the 27th
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-02-27T00:00:00.000000Z",
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 15.8


def test_manual_rides_are_typed_times_and_compare_as_typed(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        mileage.create_manual_ride(
            conn, bike_id=bike.id, distance_miles=9.0, occurred_at="2024-08-22T12:45:00.000000Z", note=None,
        )
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at=None,
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 0
