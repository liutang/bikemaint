"""The ride table as an editable log (specs/006, M3)."""

import sqlite3

import pytest

from app.db import bikes, components, connection, mileage


@pytest.fixture
def conn(db_path):
    connection.run_migrations()
    with connection.get_connection() as c:
        yield c


def _strava(conn, activity_id, bike_id, miles=10.0, when="2026-09-01T08:00:00.000000Z"):
    return mileage.upsert_ride_activity(
        conn, strava_activity_id=activity_id, strava_gear_id="g1", bike_id=bike_id,
        distance_miles=miles, occurred_at=when,
    )


def test_strava_rides_default_to_the_strava_source(conn):
    bike = bikes.create(conn, name="B")

    ride = _strava(conn, 1, bike.id)

    assert (ride.source, ride.user_modified, ride.deleted_by_user, ride.note) == ("strava", False, False, None)
    assert ride.strava_activity_id == 1


def test_manual_rides_have_no_strava_id_and_several_can_coexist(conn):
    bike = bikes.create(conn, name="B")

    a = mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=5.0, occurred_at="2026-09-02T12:00:00.000000Z", note="Commute")
    b = mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=6.0, occurred_at="2026-09-03T12:00:00.000000Z", note=None)

    assert (a.source, a.strava_activity_id, a.note) == ("manual", None, "Commute")
    assert b.id != a.id and b.strava_activity_id is None


def test_a_resync_updates_an_untouched_ride_but_not_an_edited_one(conn):
    bike = bikes.create(conn, name="B")
    untouched = _strava(conn, 1, bike.id, miles=10.0)
    edited = _strava(conn, 2, bike.id, miles=20.0)
    mileage.update_ride(conn, edited.id, bike_id=bike.id, distance_miles=18.0, occurred_at=edited.occurred_at, note="Cut short")

    _strava(conn, 1, bike.id, miles=11.0)
    after = _strava(conn, 2, bike.id, miles=21.0)  # Strava now says 21, the rider says 18

    assert mileage.get_ride(conn, untouched.id).distance_miles == 11.0
    assert after.distance_miles == 18.0 and after.user_modified is True and after.note == "Cut short"


def test_a_resync_does_not_move_a_ride_the_rider_reassigned(conn):
    mine = bikes.create(conn, name="Mine")
    other = bikes.create(conn, name="Other")
    ride = _strava(conn, 1, mine.id)
    mileage.update_ride(conn, ride.id, bike_id=other.id, distance_miles=10.0, occurred_at=ride.occurred_at, note=None)

    again = _strava(conn, 1, mine.id)

    assert again.bike_id == other.id


def test_a_ride_the_rider_deleted_stays_deleted_after_a_resync(conn):
    bike = bikes.create(conn, name="B")
    ride = _strava(conn, 1, bike.id)
    mileage.delete_ride(conn, ride.id)

    again = _strava(conn, 1, bike.id)

    assert again.deleted_by_user is True
    assert mileage.list_rides_for_bike(conn, bike.id) == []


def test_totals_ignore_user_deleted_rides(conn):
    bike = bikes.create(conn, name="B", manual_baseline_mileage=100)
    keep = _strava(conn, 1, bike.id, miles=10)
    gone = _strava(conn, 2, bike.id, miles=5)
    mileage.delete_ride(conn, gone.id)

    assert mileage.recompute_bike_total_mileage(conn, bike.id) == 110
    assert keep.id and gone.id


def test_component_totals_ignore_user_deleted_rides_and_follow_reassignment(conn):
    one = bikes.create(conn, name="One")
    two = bikes.create(conn, name="Two")
    chain = components.create(conn, name="Chain", component_type="chain", parent_bike_id=one.id)
    components.open_installation_period(conn, chain.id, parent_bike_id=one.id, parent_component_id=None,
                                         installed_at="2020-01-01T00:00:00.000000Z")
    ride = _strava(conn, 1, one.id, miles=30)
    assert mileage.recompute_component_total_mileage(conn, chain.id) == 30

    mileage.update_ride(conn, ride.id, bike_id=two.id, distance_miles=30, occurred_at=ride.occurred_at, note=None)
    assert mileage.recompute_component_total_mileage(conn, chain.id) == 0  # the ride is on the other bike now

    mileage.update_ride(conn, ride.id, bike_id=one.id, distance_miles=30, occurred_at=ride.occurred_at, note=None)
    mileage.delete_ride(conn, ride.id)
    assert mileage.recompute_component_total_mileage(conn, chain.id) == 0


def test_riding_pace_ignores_user_deleted_rides(conn):
    bike = bikes.create(conn, name="B")
    ride = _strava(conn, 1, bike.id, miles=10, when="2999-01-01T08:00:00.000000Z")
    mileage.delete_ride(conn, ride.id)

    assert mileage.recent_ride_stats_for_bike(conn, bike.id, since="2000-01-01") == (0, 0)


def test_list_rides_orders_by_time_and_excludes_upstream_deleted(conn):
    bike = bikes.create(conn, name="B")
    late = _strava(conn, 1, bike.id, when="2026-09-03T08:00:00.000000Z")
    early = mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=3, occurred_at="2026-09-01T09:00:00.000000Z", note=None)
    conn.execute("UPDATE ride_activity SET is_deleted_upstream = 1 WHERE id = ?", (late.id,))
    other = _strava(conn, 3, bike.id, when="2026-09-02T08:00:00.000000Z")

    rides = mileage.list_rides_for_bike(conn, bike.id)

    assert [r.id for r in rides] == [early.id, other.id]


def test_latest_ride_epoch_still_drives_the_incremental_sync_cursor(conn):
    bike = bikes.create(conn, name="B")
    _strava(conn, 1, bike.id, when="2026-09-03T08:00:00.000000Z")
    mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=3, occurred_at="2030-01-01T00:00:00.000000Z", note=None)

    # A manual ride in the future must not make Strava sync skip real activities.
    from datetime import datetime, timezone

    expected = int(datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc).timestamp())
    assert mileage.latest_ride_epoch(conn) == expected


def test_the_migration_keeps_existing_rides(db_path):
    from app.db.connection import MIGRATIONS_DIR

    raw = sqlite3.connect(db_path)
    for path in sorted(MIGRATIONS_DIR.glob("000[1-8]_*.sql")):
        raw.executescript(path.read_text())
    raw.execute("INSERT INTO bike (name, created_at, updated_at) VALUES ('B', 'x', 'x')")
    raw.execute(
        "INSERT INTO ride_activity (strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at, "
        "is_deleted_upstream, synced_at) VALUES (7, 'g', 1, 12.5, '2026-09-01T08:00:00.000000Z', 0, 'now')"
    )
    raw.executescript((MIGRATIONS_DIR / "0009_rides_become_a_log.sql").read_text())

    row = raw.execute(
        "SELECT source, strava_activity_id, distance_miles, user_modified, deleted_by_user FROM ride_activity"
    ).fetchone()

    assert row == ("strava", 7, 12.5, 0, 0)
