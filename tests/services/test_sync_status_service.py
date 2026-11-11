"""Sync indicator wording for the top bar (specs/003-cockpit-theme, FR-006)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db import connection, mileage
from app.services import sync_status_service

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def _stamp(delta: timedelta) -> str:
    return (NOW - delta).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@pytest.mark.parametrize(
    "delta,expected",
    [
        (timedelta(seconds=20), "Synced just now"),
        (timedelta(minutes=12), "Synced 12 min ago"),
        (timedelta(hours=3, minutes=10), "Synced 3 h ago"),
        (timedelta(days=2, hours=5), "Synced 2 d ago"),
    ],
)
def test_label_for_a_known_sync_time(delta, expected):
    assert sync_status_service.format_label(_stamp(delta), now=NOW) == expected


def test_label_when_never_synced():
    assert sync_status_service.format_label(None, now=NOW) == "Not synced yet"


def test_future_timestamps_do_not_go_negative():
    assert sync_status_service.format_label(_stamp(timedelta(minutes=-5)), now=NOW) == "Synced just now"


def test_last_sync_label_reads_the_database(db_path):
    connection.run_migrations()
    assert sync_status_service.last_sync_label(now=NOW) == "Not synced yet"
    with connection.get_connection() as conn:
        mileage.upsert_ride_activity(
            conn, strava_activity_id=9, strava_gear_id=None, bike_id=None,
            distance_miles=1.0, occurred_at="2026-10-01T08:00:00.000000Z",
        )
        conn.execute("UPDATE ride_activity SET synced_at = ?", (_stamp(timedelta(minutes=30)),))
    assert sync_status_service.last_sync_label(now=NOW) == "Synced 30 min ago"
