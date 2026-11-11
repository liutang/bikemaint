import pytest
from starlette.requests import Request

from app.db import accounts, connection
from app.services.auth_dependency import AuthRequiredError, require_account


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _request_with_session(session: dict) -> Request:
    return Request({"type": "http", "session": session, "headers": []})


def test_require_account_raises_when_session_has_no_account_id(db_path):
    with pytest.raises(AuthRequiredError):
        require_account(_request_with_session({}))


def test_require_account_raises_when_session_account_id_does_not_exist(db_path):
    with pytest.raises(AuthRequiredError):
        require_account(_request_with_session({"account_id": 999}))


def test_require_account_returns_account_for_valid_session(db_path):
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn,
            strava_athlete_id=42,
            access_token="access",
            refresh_token="refresh",
            expires_at="2026-01-01T00:00:00.000000Z",
        )

    result = require_account(_request_with_session({"account_id": account.id}))

    assert result == account
