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
