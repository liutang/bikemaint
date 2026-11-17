import pytest

from app.db import accounts, connection
from app.services import settings_service


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        return accounts.upsert_from_strava(
            conn,
            strava_athlete_id=1,
            access_token="a",
            refresh_token="r",
            expires_at="2099-01-01T00:00:00.000000Z",
        )


def test_set_and_clear_webhook_url(account):
    settings_service.set_webhook_url(account.id, "https://example.test/hook")
    assert settings_service.get_account(account.id).notification_webhook_url == (
        "https://example.test/hook"
    )

    settings_service.set_webhook_url(account.id, None)
    assert settings_service.get_account(account.id).notification_webhook_url is None


def test_set_lead_time(account):
    settings_service.set_lead_time_days(account.id, 21)

    assert settings_service.get_account(account.id).notification_lead_time_days == 21


# ------------------------------------------------ specs/023: sync settings


def test_set_sync_settings_saves_and_applies_to_the_running_scheduler(account):
    from app.services import scheduler

    scheduler.shutdown()
    instance = scheduler.start()
    try:
        settings_service.set_sync_settings(account.id, enabled=True, interval_minutes=90)

        saved = settings_service.get_account(account.id)
        assert (saved.strava_sync_enabled, saved.strava_sync_interval_minutes) == (True, 90)
        assert instance.get_job("strava_sync").trigger.interval.total_seconds() == 90 * 60

        settings_service.set_sync_settings(account.id, enabled=False, interval_minutes=90)
        assert instance.get_job("strava_sync") is None
    finally:
        scheduler.shutdown()


def test_set_sync_settings_logs_the_change_without_secrets(account, caplog):
    with caplog.at_level("INFO"):
        settings_service.set_sync_settings(account.id, enabled=True, interval_minutes=45)

    assert "enabled=True" in caplog.text and "interval_minutes=45" in caplog.text
    assert "refresh" not in caplog.text.lower() and "token" not in caplog.text.lower()


def test_effective_interval_is_the_saved_value_else_the_environment_else_thirty(account, monkeypatch):
    monkeypatch.delenv("STRAVA_SYNC_INTERVAL_MINUTES", raising=False)
    assert settings_service.effective_sync_interval(settings_service.get_account(account.id)) == 30

    monkeypatch.setenv("STRAVA_SYNC_INTERVAL_MINUTES", "20")
    assert settings_service.effective_sync_interval(settings_service.get_account(account.id)) == 20

    settings_service.set_sync_settings(account.id, enabled=True, interval_minutes=135)
    assert settings_service.effective_sync_interval(settings_service.get_account(account.id)) == 135


@pytest.mark.parametrize("minutes,expected", [(5, (0, 5)), (90, (1, 30)), (135, (2, 15)), (10080, (168, 0)), (60, (1, 0))])
def test_minutes_split_into_hours_and_minutes_for_the_form(minutes, expected):
    assert settings_service.split_minutes(minutes) == expected


@pytest.mark.parametrize("minutes,text", [(5, "5 min"), (60, "1 h"), (90, "1 h 30 min"), (135, "2 h 15 min"), (10080, "168 h")])
def test_the_interval_reads_back_in_hours_and_minutes(minutes, text):
    assert settings_service.describe_interval(minutes) == text


def test_set_timezone_saves_the_zone(account):
    settings_service.set_timezone(account.id, "Europe/London")

    assert settings_service.get_account(account.id).timezone == "Europe/London"


# ------------------------------------------------ specs/075 US4: maintenance follows a zone change


def test_a_zone_change_moves_timed_entries_and_keeps_untimed_dates(account):
    from app.db import mileage as mileage_db
    from app.services import bike_service, maintenance_service

    settings_service.set_timezone(account.id, "America/New_York")
    bike = bike_service.create_bike(name="Road", manual_baseline_mileage=0.0)
    with connection.get_connection() as conn:
        mileage_db.create_manual_ride(conn, bike_id=bike.id, distance_miles=4, occurred_at="2026-11-16T22:39:00.000000Z", note=None)
        mileage_db.recompute_bike_total_mileage(conn, bike.id)
    timed = maintenance_service.log_maintenance(bike_id=bike.id, description="Lube/Wax", performed_at="2026-11-16", performed_time="21:00")
    untimed = maintenance_service.log_maintenance(bike_id=bike.id, description="Clean", performed_at="2026-11-16")

    settings_service.set_timezone(account.id, "America/Los_Angeles")

    with connection.get_connection() as conn:
        from app.db import maintenance as maintenance_db

        t = maintenance_db.get_by_id(conn, timed.id)
        u = maintenance_db.get_by_id(conn, untimed.id)
        ride_at = conn.execute("SELECT occurred_at FROM ride_activity").fetchone()[0]
    assert (t.performed_at, t.performed_time, t.performed_instant) == ("2026-11-16", "18:00", timed.performed_instant)
    assert (u.performed_at, u.performed_time) == ("2026-11-16", None)
    assert u.performed_instant == "2026-11-17T07:59:59.999999Z"  # end of the 16th in Los Angeles
    assert ride_at == "2026-11-16T22:39:00.000000Z"  # rides do not move
    assert bike_service.get_bike(bike.id).total_mileage == 4
