import pytest

from app.db import connection
from app.services import auth_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_complete_strava_login_exchanges_code_and_upserts_account(db_path, monkeypatch):
    monkeypatch.setattr(
        auth_service.strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 1893456000,
            "athlete": {"id": 42},
        },
    )

    account = auth_service.complete_strava_login("auth-code")

    assert account.strava_athlete_id == 42
    assert account.strava_access_token == "access-token"
    assert account.strava_refresh_token == "refresh-token"
    assert account.strava_token_expires_at == "2030-01-01T00:00:00.000000Z"

    with connection.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM account").fetchone()["c"]
    assert count == 1


def test_complete_strava_login_upserts_same_account_on_repeat_login(db_path, monkeypatch):
    monkeypatch.setattr(
        auth_service.strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token-1",
            "refresh_token": "refresh-token-1",
            "expires_at": 1893456000,
            "athlete": {"id": 42},
        },
    )
    first = auth_service.complete_strava_login("auth-code-1")

    monkeypatch.setattr(
        auth_service.strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token-2",
            "refresh_token": "refresh-token-2",
            "expires_at": 1893456000,
            "athlete": {"id": 42},
        },
    )
    second = auth_service.complete_strava_login("auth-code-2")

    assert second.id == first.id
    assert second.strava_access_token == "access-token-2"
