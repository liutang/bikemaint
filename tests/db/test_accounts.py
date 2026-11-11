import pytest

from app.db import accounts, connection


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_upsert_from_strava_creates_new_account(db_path):
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn,
            strava_athlete_id=42,
            access_token="access-1",
            refresh_token="refresh-1",
            expires_at="2026-01-01T00:00:00.000000Z",
        )

    assert account.strava_athlete_id == 42
    assert account.strava_access_token == "access-1"
    assert account.strava_refresh_token == "refresh-1"
    assert account.strava_connection_stale is False


def test_upsert_from_strava_updates_existing_account_by_athlete_id(db_path):
    with connection.get_connection() as conn:
        first = accounts.upsert_from_strava(
            conn,
            strava_athlete_id=42,
            access_token="access-1",
            refresh_token="refresh-1",
            expires_at="2026-01-01T00:00:00.000000Z",
        )

    with connection.get_connection() as conn:
        second = accounts.upsert_from_strava(
            conn,
            strava_athlete_id=42,
            access_token="access-2",
            refresh_token="refresh-2",
            expires_at="2026-02-01T00:00:00.000000Z",
        )

    assert second.id == first.id
    assert second.strava_access_token == "access-2"
    assert second.strava_refresh_token == "refresh-2"

    with connection.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM account").fetchone()["c"]
    assert count == 1


def test_get_by_id_returns_none_when_missing(db_path):
    with connection.get_connection() as conn:
        assert accounts.get_by_id(conn, 999) is None


def test_get_by_strava_athlete_id_returns_none_when_missing(db_path):
    with connection.get_connection() as conn:
        assert accounts.get_by_strava_athlete_id(conn, 999) is None
