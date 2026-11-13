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
