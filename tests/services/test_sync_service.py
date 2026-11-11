"""Tests for the not-yet-implemented `app/services/sync_service.py` (User Story 2).

These are written ahead of the implementation per the constitution's TDD mandate
(Principle III) — expect them to fail (missing module) until T035-T047 land.
"""

import pytest

from app.db import accounts, connection
from app.services import bike_service, component_service, strava_client, sync_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _connected_account() -> accounts.Account:
    with connection.get_connection() as conn:
        return accounts.upsert_from_strava(
            conn,
            strava_athlete_id=1,
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at="2099-01-01T00:00:00.000000Z",
        )


def _pair_bike_to_gear(bike_id: int, strava_gear_id: str) -> None:
    with connection.get_connection() as conn:
        conn.execute(
            "UPDATE bike SET strava_gear_id = ? WHERE id = ?", (strava_gear_id, bike_id)
        )


def test_sync_credits_bike_and_components_installed_at_ride_time(db_path, monkeypatch):
    account = _connected_account()
    bike = bike_service.create_bike(name="Gravel Bike")
    _pair_bike_to_gear(bike.id, "gear-1")

    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike.id
    )
    # Back-date the wheel's installation period so the first ride below predates it
    # (Acceptance Scenario US2-2: mileage before install must not attribute to it).
    with connection.get_connection() as conn:
        conn.execute(
            "UPDATE component_installation_period SET installed_at = ? WHERE component_id = ?",
            ("2026-09-05T00:00:00.000000Z", wheel.id),
        )

    activities = [
        {  # before the wheel was installed
            "id": 1001,
            "gear_id": "gear-1",
            "distance": 16093.4,  # 10.0 mi
            "start_date": "2026-09-01T08:00:00Z",
        },
        {  # after the wheel was installed
            "id": 1002,
            "gear_id": "gear-1",
            "distance": 32186.8,  # 20.0 mi
            "start_date": "2026-09-10T08:00:00Z",
        },
    ]
    monkeypatch.setattr(strava_client, "get_activities", lambda access_token, **kwargs: activities)

    sync_service.sync_incremental(account.id)

    updated_bike = bike_service.get_bike(bike.id)
    updated_wheel = component_service.get_component(wheel.id)
    assert updated_bike.total_mileage == pytest.approx(30.0)
    assert updated_wheel.total_mileage == pytest.approx(20.0)


def test_sync_does_not_attribute_activity_for_unmapped_gear(db_path, monkeypatch):
    account = _connected_account()
    bike = bike_service.create_bike(name="Gravel Bike")
    _pair_bike_to_gear(bike.id, "gear-1")

    activities = [
        {
            "id": 2001,
            "gear_id": "some-other-unmapped-gear",
            "distance": 16093.4,
            "start_date": "2026-09-10T08:00:00Z",
        }
    ]
    monkeypatch.setattr(strava_client, "get_activities", lambda access_token, **kwargs: activities)

    sync_service.sync_incremental(account.id)

    updated_bike = bike_service.get_bike(bike.id)
    assert updated_bike.total_mileage == pytest.approx(0.0)


def test_backfill_bike_imports_full_ride_history_on_pairing(db_path, monkeypatch):
    account = _connected_account()
    bike = bike_service.create_bike(name="Road Bike")
    _pair_bike_to_gear(bike.id, "gear-2")

    activities = [
        {"id": 3001, "gear_id": "gear-2", "distance": 16093.4, "start_date": "2020-01-01T08:00:00Z"},
        {"id": 3002, "gear_id": "gear-2", "distance": 16093.4, "start_date": "2026-09-01T08:00:00Z"},
    ]
    monkeypatch.setattr(strava_client, "get_activities", lambda access_token, **kwargs: activities)

    sync_service.backfill_bike(bike.id)

    updated_bike = bike_service.get_bike(bike.id)
    assert updated_bike.total_mileage == pytest.approx(20.0)


def test_adjust_bike_mileage_records_signed_delta_and_updates_total(db_path):
    bike = bike_service.create_bike(name="Commuter", manual_baseline_mileage=100.0)

    updated = sync_service.adjust_bike_mileage(bike.id, delta_miles=-5.0, reason="Misattributed ride")

    assert updated.total_mileage == pytest.approx(95.0)
    with connection.get_connection() as conn:
        row = conn.execute(
            "SELECT delta_miles, reason FROM mileage_adjustment WHERE bike_id = ?", (bike.id,)
        ).fetchone()
    assert row["delta_miles"] == pytest.approx(-5.0)
    assert row["reason"] == "Misattributed ride"


def test_adjust_component_mileage_records_signed_delta_and_updates_total_without_a_reason(db_path):
    component = component_service.create_component(
        name="Chain", component_type="chain", manual_baseline_mileage=50.0
    )

    updated = sync_service.adjust_component_mileage(component.id, delta_miles=10.0)

    assert updated.total_mileage == pytest.approx(60.0)
    with connection.get_connection() as conn:
        row = conn.execute(
            "SELECT delta_miles, reason FROM mileage_adjustment WHERE component_id = ?",
            (component.id,),
        ).fetchone()
    assert row["delta_miles"] == pytest.approx(10.0)
    assert row["reason"] is None


def test_incremental_sync_logs_a_readable_summary(db_path, monkeypatch, caplog):
    account = _connected_account()
    bike = bike_service.create_bike(name="Gravel Bike")
    _pair_bike_to_gear(bike.id, "gear-1")
    monkeypatch.setattr(
        strava_client,
        "get_activities",
        lambda access_token, **kwargs: [
            {
                "id": 1,
                "gear_id": "gear-1",
                "distance": 16093.4,
                "start_date": "2026-09-01T08:00:00Z",
            }
        ],
    )

    with caplog.at_level("INFO"):
        sync_service.sync_incremental(account.id)

    assert f"account_id={account.id}" in caplog.text
    assert "activities=1" in caplog.text
    assert "access-token" not in caplog.text


def test_sync_skipped_for_stale_connection_is_logged_as_a_warning(db_path, monkeypatch, caplog):
    account = _connected_account()

    def stale(_account):
        raise strava_client.StravaTokenRefreshError("revoked")

    monkeypatch.setattr(strava_client, "ensure_fresh_access_token", stale)

    with caplog.at_level("WARNING"):
        sync_service.sync_incremental(account.id)

    assert any(
        record.levelname == "WARNING" and f"account_id={account.id}" in record.getMessage()
        for record in caplog.records
    )


def test_backfill_twice_does_not_duplicate_rides(db_path, monkeypatch):
    _connected_account()
    from app.db import connection, mileage
    from app.services import bike_service

    bike = bike_service.create_bike_from_details(year=2023, make="Trek", model="Madone", category="road")
    monkeypatch.setattr(strava_client, "ensure_fresh_access_token", lambda account: "t")
    activities = [{"id": 7, "gear_id": "b1", "distance": 16093.4, "start_date": "2024-01-01T10:00:00Z"}]
    monkeypatch.setattr(strava_client, "get_activities", lambda access_token, **kwargs: activities)
    with connection.get_connection() as conn:
        from app.db import bikes as bikes_db
        bikes_db.set_strava_pairing(conn, bike.id, strava_gear_id="b1", strava_paired_at="2024-01-01T00:00:00.000000Z")

    sync_service.backfill_bike(bike.id)
    sync_service.backfill_bike(bike.id)

    with connection.get_connection() as conn:
        assert len(mileage.list_rides_for_bike(conn, bike.id)) == 1
