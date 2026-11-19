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

    assert data["app"] == "bikemaint" and data["format"] == 2
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



# ------------------------------------------------ specs/075: format 2, and older files are converted on restore


def test_a_new_backup_is_format_2_and_carries_each_entrys_instant(db_path):
    _fill()
    data = backup_service.export_backup()
    assert data["format"] == 2
    assert all("performed_instant" in row for row in data["tables"]["maintenance_log_entry"])


def _format_1_file():
    """A backup as an older version wrote it: typed times as typed, no performed_instant."""
    bike = bike_service.create_bike(name="Road")
    part = component_service.create_component(name="Chain", component_type="chain")
    data = backup_service.export_backup()
    data["format"] = 1
    data["settings"]["timezone"] = "America/New_York"
    data["tables"]["ride_activity"] = [{
        "id": 1, "source": "manual", "strava_activity_id": None, "strava_gear_id": None, "bike_id": bike.id,
        "distance_miles": 5.0, "occurred_at": "2026-11-16T17:00:00.000000Z", "synced_at": None,
        "is_deleted_upstream": 0, "note": None, "user_modified": 1, "deleted_by_user": 0,
    }]
    data["tables"]["component_installation_period"] = [{
        "id": 1, "component_id": part.id, "parent_bike_id": bike.id, "parent_component_id": None,
        "installed_at": "2026-11-01T08:00:00.000000Z", "removed_at": None,
    }]
    data["tables"]["maintenance_log_entry"] = [{
        "id": 1, "bike_id": bike.id, "component_id": None, "description": "Lube/Wax", "performed_at": "2026-11-16",
        "performed_time": "21:00", "mileage_at_service": 3.0, "schedule_id": None, "kind": "service",
        "created_at": "2026-11-17T02:05:00.000000Z", "updated_at": "2026-11-17T02:05:00.000000Z",
    }]
    return data


def test_restoring_an_older_backup_converts_its_typed_times_with_its_zone(db_path):
    data = _format_1_file()
    with connection.get_connection() as conn:  # the zone saved here must not be the one used
        conn.execute("UPDATE account SET timezone = 'Europe/London'")

    backup_service.restore_backup(data)

    with connection.get_connection() as conn:
        assert conn.execute("SELECT occurred_at FROM ride_activity").fetchone()[0] == "2026-11-16T22:00:00.000000Z"
        assert conn.execute("SELECT installed_at FROM component_installation_period").fetchone()[0] == "2026-11-01T13:00:00.000000Z"
        row = conn.execute("SELECT performed_at, performed_time, performed_instant FROM maintenance_log_entry").fetchone()
        assert tuple(row) == ("2026-11-16", "21:00", "2026-11-17T02:00:00.000000Z")


def test_restoring_a_format_2_backup_converts_nothing(db_path):
    with connection.get_connection() as conn:
        conn.execute("UPDATE account SET timezone = 'America/New_York'")
    bike = bike_service.create_bike(name="Road")
    maintenance_service.log_maintenance(bike_id=bike.id, description="Lube/Wax", performed_at="2026-11-16", performed_time="21:00")
    with connection.get_connection() as conn:
        mileage_db.create_manual_ride(conn, bike_id=bike.id, distance_miles=1, occurred_at="2026-11-16T22:00:00.000000Z", note=None)
    before = _snapshot()

    backup_service.restore_backup(json.loads(json.dumps(backup_service.export_backup())))

    assert _snapshot() == before


def test_a_64_bit_activity_id_survives_a_backup_and_restore_exactly(db_path):
    """Strava 64-bit ids (017 T020): the JSON file and the restore keep an id above 2**53 exact."""
    big_id = 2**62 + 12345
    bike = bike_service.create_bike(name="Road")
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=big_id, strava_gear_id="g", bike_id=bike.id,
                                        distance_miles=10.0, occurred_at="2027-06-02T08:00:00.000000Z")
    data = json.loads(json.dumps(backup_service.export_backup()))
    with connection.get_connection() as conn:
        conn.execute("DELETE FROM ride_activity")

    backup_service.restore_backup(data)

    with connection.get_connection() as conn:
        assert [r[0] for r in conn.execute("SELECT strava_activity_id FROM ride_activity")] == [big_id]


# ------------------------------------------------ specs/076 US3: restore repairs short years


def test_restoring_a_backup_with_the_old_pads_value_repairs_it(db_path):
    bike = bike_service.create_bike(name="Madone")
    pads = component_service.create_component(name="GRX pads", component_type="brake_pad")
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=1, strava_gear_id="g", bike_id=bike.id,
                                        distance_miles=30.0, occurred_at="2024-05-01T12:00:00.000000Z")
    data = backup_service.export_backup()
    data["tables"]["component_installation_period"] = [{
        "id": 1, "component_id": pads.id, "parent_bike_id": bike.id, "parent_component_id": None,
        "installed_at": "21-04-18T04:56:02.000000Z", "removed_at": None,
    }]

    backup_service.restore_backup(json.loads(json.dumps(data)))

    with connection.get_connection() as conn:
        assert conn.execute("SELECT installed_at FROM component_installation_period").fetchone()[0] == "2021-04-18T04:00:00.000000Z"
    assert component_service.get_component(pads.id).total_mileage == 30.0


def test_an_older_backup_with_a_two_digit_typed_year_is_converted_and_repaired(db_path):
    data = _format_1_file()
    data["tables"]["maintenance_log_entry"][0]["performed_at"] = "0026-11-16"

    backup_service.restore_backup(data)

    with connection.get_connection() as conn:
        row = conn.execute("SELECT performed_at, performed_instant FROM maintenance_log_entry").fetchone()
    assert tuple(row) == ("2026-11-16", "2026-11-17T02:00:00.000000Z")


# ------------------------------------------------ specs/079: backups carry the archived state


def test_archived_state_survives_a_backup_and_an_older_file_restores_as_active(db_path):
    from app.services import archive_service

    bike = bike_service.create_bike(name="Old Road")
    spare = component_service.create_component(name="Spare", component_type="chain")
    archive_service.archive_bike(bike.id, attached=None)
    archive_service.archive_part(spare.id, attached=None)
    data = json.loads(json.dumps(backup_service.export_backup()))
    archived_at = bike_service.get_bike(bike.id).archived_at

    backup_service.restore_backup(data)
    assert bike_service.get_bike(bike.id).archived_at == archived_at
    assert component_service.get_component(spare.id).archived_at is not None

    for table in ("bike", "component"):
        for row in data["tables"][table]:
            row.pop("archived_at")
    backup_service.restore_backup(data)
    assert bike_service.get_bike(bike.id).archived_at is None
    assert component_service.get_component(spare.id).archived_at is None


def test_usage_leads_round_trip_and_an_older_file_keeps_the_defaults(db_path):
    """specs/086 FR-001."""
    with connection.get_connection() as conn:
        conn.execute("UPDATE account SET lead_miles = 30, lead_rides = 4, lead_hours = 3")
    data = json.loads(json.dumps(backup_service.export_backup()))
    assert (data["settings"]["lead_miles"], data["settings"]["lead_rides"], data["settings"]["lead_hours"]) == (30, 4, 3)
    with connection.get_connection() as conn:
        conn.execute("UPDATE account SET lead_miles = 20, lead_rides = 2, lead_hours = 2")
    backup_service.restore_backup(data)
    with connection.get_connection() as conn:
        assert tuple(conn.execute("SELECT lead_miles, lead_rides, lead_hours FROM account").fetchone()) == (30, 4, 3)
    for key in ("lead_miles", "lead_rides", "lead_hours"):
        data["settings"].pop(key)
    backup_service.restore_backup(data)
    with connection.get_connection() as conn:
        assert tuple(conn.execute("SELECT lead_miles, lead_rides, lead_hours FROM account").fetchone()) == (30, 4, 3)
