"""Mileage as of a moment (specs/038-maintenance-mileage-at-date)."""

import pytest

from app.db import bikes, connection, mileage


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def test_adjustments_count_in_full_and_later_rides_do_not(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road", manual_baseline_mileage=10.0)
        mileage.upsert_ride_activity(
            conn, strava_activity_id=1, strava_gear_id="g", bike_id=bike.id,
            distance_miles=5, occurred_at="2026-04-01T08:00:00.000000Z",
        )
        mileage.upsert_ride_activity(
            conn, strava_activity_id=2, strava_gear_id="g", bike_id=bike.id,
            distance_miles=7, occurred_at="2026-06-01T08:00:00.000000Z",
        )
        mileage.insert_mileage_adjustment(conn, bike_id=bike.id, component_id=None, delta_miles=-2, reason="fix")

        assert mileage.bike_mileage_at(conn, bike.id, "2026-05-01T00:00:00.000000Z") == 13
        assert mileage.bike_mileage_at(conn, bike.id, "2027-01-01T00:00:00.000000Z") == 20
        with pytest.raises(LookupError):
            mileage.bike_mileage_at(conn, 999, "2027-01-01T00:00:00.000000Z")
