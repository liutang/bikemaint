"""Backup and restore (specs/067-backup-restore)."""

import json

import pytest

from app.db import accounts, connection, mileage as mileage_db
from app.services import (
    backup_service, bike_service, component_history_service as history, component_service,
    maintenance_service, schedule_service, sync_rule_service,
)

D = "T00:00:00.000000Z"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        a = accounts.upsert_from_strava(conn, strava_athlete_id=1, access_token="SECRET-A", refresh_token="SECRET-R",
                                        expires_at="2099-01-01T00:00:00Z")
        accounts.update_timezone(conn, a.id, "America/New_York")
        conn.execute("UPDATE account SET notification_webhook_url = 'https://hook.example/SECRET', notification_lead_time_days = 11")


def _fill():
    bike = bike_service.create_bike(name="Road")
    wheels = component_service.create_component(name="Wheelset", component_type="wheel")
    tire = component_service.create_component(name="Tire", component_type="tire")
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2023-01-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-02-01" + D, removed_at="2022-12-01" + D)
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=1, strava_gear_id="g", bike_id=bike.id,
                                        distance_miles=12.5, occurred_at="2022-05-01T12:00:00.000000Z")
    maintenance_service.log_maintenance(component_id=tire.id, description="Clean", mileage_at_service=0, performed_at="2022-05-02")
    schedule_service.create_schedule(bike_id=bike.id, service_type="Check", interval_kind="period", interval_value=2, interval_unit="months")
    sync_rule_service.save_rule("component", tire.id, sports=["Ride"], ride_types=[], keywords="x")
    return bike, wheels, tire


def _snapshot():
    data = backup_service.export_backup()
    # updated_at and the totals are re-stamped when totals are recomputed, so it is not part of "the same records".
    return {name: [{k: v for k, v in r.items() if k not in ("updated_at", "total_mileage")} for r in rows] for name, rows in data["tables"].items()}


def test_the_export_has_every_table_and_no_secrets(db_path):
    _fill()

    data = backup_service.export_backup()
    text = json.dumps(data)

    assert data["app"] == "bikemaint" and data["format"] == 1
    assert len(data["tables"]["bike"]) == 1 and len(data["tables"]["component"]) == 2
    assert len(data["tables"]["component_installation_period"]) >= 2 and len(data["tables"]["ride_activity"]) == 1
    assert "SECRET" not in text and "access_token" not in text
    assert data["settings"]["timezone"] == "America/New_York" and data["settings"]["notification_lead_time_days"] == 11


def test_restoring_into_an_empty_database_reproduces_everything(db_path):
    bike, wheels, tire = _fill()
    before = _snapshot()
    data = json.loads(json.dumps(backup_service.export_backup()))
    with connection.get_connection() as conn:
        for table in reversed(list(before)):
            conn.execute(f"DELETE FROM {table}")

    counts = backup_service.restore_backup(data)

    assert _snapshot() == before
    assert counts["bike"] == 1 and counts["component"] == 2 and counts["ride_activity"] == 1
    assert component_service.get_component(tire.id).total_mileage == 12.5


def test_restore_replaces_what_is_there_and_keeps_the_account_secrets(db_path):
    _fill()
    data = backup_service.export_backup()
    bike_service.create_bike(name="Newer bike")
    with connection.get_connection() as conn:
        conn.execute("UPDATE account SET timezone = 'UTC', notification_lead_time_days = 3")

    backup_service.restore_backup(data)

    assert [b.name for b in bike_service.list_bikes()] == ["Road"]
    with connection.get_connection() as conn:
        a = conn.execute("SELECT * FROM account").fetchone()
    assert (a["timezone"], a["notification_lead_time_days"]) == ("America/New_York", 11)
    assert a["strava_access_token"] == "SECRET-A" and a["notification_webhook_url"] == "https://hook.example/SECRET"


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"app": "other", "format": 1, "tables": {}}',
                                 b'{"app": "bikemaint", "format": 99, "tables": {}}'])
def test_files_that_are_not_a_backup_are_refused(db_path, raw):
    with pytest.raises(ValueError):
        backup_service.parse_backup(raw)


def test_a_bad_file_changes_nothing(db_path):
    _fill()
    before = _snapshot()
    data = backup_service.export_backup()
    data["tables"]["bike"][0]["no_such_column"] = 1

    with pytest.raises(ValueError, match="newer"):
        backup_service.restore_backup(data)

    data = backup_service.export_backup()
    data["tables"]["component"][0]["parent_bike_id"] = 999  # points at no bike
    with pytest.raises(ValueError):
        backup_service.restore_backup(data)
    assert _snapshot() == before

