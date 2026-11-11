"""`app/db/mileage.py::latest_synced_at` backs the top-bar sync indicator (003-cockpit-theme)."""

import pytest

from app.db import connection, mileage


@pytest.fixture
def migrated(db_path):
    connection.run_migrations()


def test_latest_synced_at_is_none_without_rides(migrated):
    with connection.get_connection() as conn:
        assert mileage.latest_synced_at(conn) is None


def test_latest_synced_at_returns_the_newest_sync_time(migrated):
    with connection.get_connection() as conn:
        for activity_id, synced in ((1, "2026-11-01T08:00:00.000000Z"), (2, "2026-11-05T09:30:00.000000Z")):
            mileage.upsert_ride_activity(
                conn,
                strava_activity_id=activity_id,
                strava_gear_id=None,
                bike_id=None,
                distance_miles=5.0,
                occurred_at="2026-10-01T08:00:00.000000Z",
            )
            conn.execute(
                "UPDATE ride_activity SET synced_at = ? WHERE strava_activity_id = ?",
                (synced, activity_id),
            )
        assert mileage.latest_synced_at(conn) == "2026-11-05T09:30:00.000000Z"
