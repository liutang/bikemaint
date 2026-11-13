import pytest

from app.services import scheduler


@pytest.fixture(autouse=True)
def _clean_scheduler():
    scheduler.shutdown()
    yield
    scheduler.shutdown()


def test_start_registers_sync_and_notification_jobs():
    instance = scheduler.start()

    assert {job.id for job in instance.get_jobs()} == {"strava_sync", "due_notifications"}


def test_notification_job_interval_is_env_configurable(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHECK_INTERVAL_MINUTES", "15")

    instance = scheduler.start()

    job = instance.get_job("due_notifications")
    assert job.trigger.interval.total_seconds() == 15 * 60


def test_notification_job_runs_the_due_check(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler.notification_service, "check_due_schedules", lambda: calls.append(1))

    scheduler._run_notification_job()

    assert calls == [1]


def test_notification_job_swallows_and_logs_failures(monkeypatch):
    def boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(scheduler.notification_service, "check_due_schedules", boom)

    scheduler._run_notification_job()  # must not raise


# ------------------------------------------------ specs/023: rider-controlled sync interval


def _minutes(instance):
    return instance.get_job("strava_sync").trigger.interval.total_seconds() / 60


def test_start_uses_the_environment_default_until_the_rider_saves(monkeypatch):
    monkeypatch.setenv("STRAVA_SYNC_INTERVAL_MINUTES", "45")

    assert _minutes(scheduler.start()) == 45


def test_start_defaults_to_thirty_minutes(monkeypatch):
    monkeypatch.delenv("STRAVA_SYNC_INTERVAL_MINUTES", raising=False)

    assert _minutes(scheduler.start()) == 30


def test_apply_sync_settings_replaces_the_job_in_place():
    instance = scheduler.start()

    scheduler.apply_sync_settings(True, 90)
    scheduler.apply_sync_settings(True, 135)

    assert [j.id for j in instance.get_jobs()].count("strava_sync") == 1
    assert _minutes(instance) == 135


def test_apply_sync_settings_off_removes_only_the_sync_job_and_on_restores_it():
    instance = scheduler.start()

    scheduler.apply_sync_settings(False, 90)
    assert {j.id for j in instance.get_jobs()} == {"due_notifications"}

    scheduler.apply_sync_settings(True, 90)
    assert {j.id for j in instance.get_jobs()} == {"strava_sync", "due_notifications"}
    assert _minutes(instance) == 90


def test_apply_sync_settings_does_nothing_when_the_scheduler_is_not_running():
    scheduler.apply_sync_settings(True, 90)  # no error, nothing to change


def test_start_reads_the_saved_settings(tmp_path, monkeypatch):
    from app.db import accounts, connection

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn, strava_athlete_id=1, access_token="a", refresh_token="r",
            expires_at="2026-01-01T00:00:00.000000Z",
        )
        accounts.update_sync_settings(conn, account.id, enabled=True, interval_minutes=75)

    assert _minutes(scheduler.start()) == 75


def test_start_registers_no_sync_job_when_the_rider_turned_it_off(tmp_path, monkeypatch):
    from app.db import accounts, connection

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn, strava_athlete_id=1, access_token="a", refresh_token="r",
            expires_at="2026-01-01T00:00:00.000000Z",
        )
        accounts.update_sync_settings(conn, account.id, enabled=False, interval_minutes=75)

    instance = scheduler.start()

    assert {j.id for j in instance.get_jobs()} == {"due_notifications"}
