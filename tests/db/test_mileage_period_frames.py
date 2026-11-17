"""Install periods and rides are compared as UTC instants (specs/075, which replaced 015 FR-013 and 051).

Strava rides and every typed time are stored in UTC, so a period starting 12:51PM EDT
(16:51 UTC) must not include a ride that started 12:41PM EDT (16:41 UTC). The cases are the
ones 051 fixed, with typed times now given in UTC.
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
            installed_at="2024-08-22T16:51:00.000000Z",   # typed: 12:51PM EDT
            removed_at="2025-02-27T05:00:00.000000Z",     # typed: midnight EST
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
            installed_at="2024-08-22T16:51:00.000000Z", removed_at=None,
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 10.0


def test_a_ride_late_on_the_removal_day_is_excluded_after_a_midnight_removal(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        _strava(conn, bike, 1, 15.8, "2025-02-27T04:30:00.000000Z")  # 11:30PM EST on the 26th
        _strava(conn, bike, 2, 5.0, "2025-02-27T05:30:00.000000Z")   # 12:30AM EST on the 27th
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2025-01-01T05:00:00.000000Z", removed_at="2025-02-27T05:00:00.000000Z",
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 15.8


def test_manual_rides_compare_as_instants_too(db_path):
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        mileage.create_manual_ride(
            conn, bike_id=bike.id, distance_miles=9.0, occurred_at="2024-08-22T16:45:00.000000Z", note=None,
        )  # typed 12:45PM EDT
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T16:51:00.000000Z", removed_at=None,
        )
        assert mileage.recompute_component_total_mileage(conn, part.id) == 0


def test_the_two_clock_sql_functions_are_gone(db_path):
    with connection.get_connection() as conn:
        for call in ("ride_wall('2024-01-01T00:00:00.000000Z', 'strava')", "period_wall('2024-01-01T00:00:00.000000Z')"):
            with pytest.raises(Exception, match="no such function"):
                conn.execute(f"SELECT {call}").fetchone()


def test_a_ride_shortly_before_a_service_time_is_before_it(db_path):
    """The Background bug: 2:26PM EST (19:26 UTC) was compared with a typed 15:00 and counted after it."""
    with connection.get_connection() as conn:
        bike, part = _setup(conn)
        _strava(conn, bike, 1, 12.0, "2026-11-13T19:26:41.000000Z")  # 2:26PM EST
        service = "2026-11-13T20:00:00.000000Z"  # 3:00PM EST

        assert mileage.usage_since(conn, bike_id=bike.id, since=service) == (0, 0)
        assert mileage.bike_mileage_at(conn, bike.id, service) == 12.0
