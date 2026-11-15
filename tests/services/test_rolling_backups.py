"""Dated names and rolling backups to a volume (specs/068-rolling-backups)."""

import json
from datetime import datetime, timezone

import pytest

from app.db import accounts, connection
from app.services import backup_service, bike_service, scheduler


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        a = accounts.upsert_from_strava(conn, strava_athlete_id=1, access_token="a", refresh_token="r", expires_at="2099-01-01T00:00:00Z")
        accounts.update_timezone(conn, a.id, "America/New_York")


def test_the_file_name_has_the_date_and_time_in_the_saved_zone(db_path):
    name = backup_service.backup_filename(datetime(2026, 11, 15, 19, 5, 9, tzinfo=timezone.utc))

    assert name == "bikemaint-backup-2026-11-15-140509.json"  # 19:05 UTC is 14:05 in New York


def test_config_reads_the_environment_and_falls_back_on_bad_values(monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    assert backup_service.rolling_config() is None

    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    assert backup_service.rolling_config() == (tmp_path, 7, 24)
    monkeypatch.setenv("BACKUP_KEEP", "3")
    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "6")
    assert backup_service.rolling_config() == (tmp_path, 3, 6)
    monkeypatch.setenv("BACKUP_KEEP", "0")
    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "x")
    assert backup_service.rolling_config() == (tmp_path, 7, 24)


def test_a_backup_is_written_as_restorable_json_and_only_the_newest_n_stay(db_path, monkeypatch, tmp_path):
    folder = tmp_path / "nas"
    folder.mkdir()
    (folder / "notes.txt").write_text("keep me")
    (folder / "bikemaint-backup-2020-01-01-000000.json.bak").write_text("not a backup name")
    monkeypatch.setenv("BACKUP_DIR", str(folder))
    monkeypatch.setenv("BACKUP_KEEP", "3")
    bike_service.create_bike(name="Road")

    for second in range(5):
        backup_service.write_rolling_backup(now=datetime(2026, 11, 15, 12, 0, second, tzinfo=timezone.utc))

    kept = backup_service.list_rolling_backups()
    assert [p.name for p in kept] == [
        "bikemaint-backup-2026-11-15-070004.json", "bikemaint-backup-2026-11-15-070003.json",
        "bikemaint-backup-2026-11-15-070002.json"]
    assert (folder / "notes.txt").exists() and (folder / "bikemaint-backup-2020-01-01-000000.json.bak").exists()
    assert not list(folder.glob("*.tmp"))
    assert json.loads(kept[0].read_text())["tables"]["bike"][0]["name"] == "Road"


def test_two_backups_in_one_second_do_not_overwrite(db_path, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)

    one = backup_service.write_rolling_backup(now=now)
    two = backup_service.write_rolling_backup(now=now)

    assert one != two and one.exists() and two.exists()


def test_an_unwritable_folder_raises_for_the_button_but_the_job_only_logs(db_path, monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "missing" / "deeper"))
    with pytest.raises(OSError):
        backup_service.write_rolling_backup()

    scheduler._run_backup_job()  # must not raise

    assert "rolling backup failed" in caplog.text


def test_the_job_is_scheduled_only_when_a_folder_is_set(db_path, monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    s = scheduler.start()
    assert s.get_job("rolling_backup") is None
    scheduler.shutdown()

    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    s = scheduler.start()
    try:
        assert s.get_job("rolling_backup") is not None
    finally:
        scheduler.shutdown()
