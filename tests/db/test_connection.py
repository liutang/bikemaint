import pytest

from app.db import connection


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return path


def test_run_migrations_creates_expected_tables_and_records_schema_version(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        versions = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_version").fetchall()
        }

    assert {
        "account",
        "bike",
        "component",
        "component_installation_period",
    } <= tables
    assert "0001_initial.sql" in versions


def test_run_migrations_is_idempotent(db_path):
    connection.run_migrations()
    connection.run_migrations()

    with connection.get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM schema_version WHERE version = '0001_initial.sql'"
        ).fetchone()["c"]

    assert count == 1


def test_account_requires_unique_strava_athlete_id(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO account (
                strava_athlete_id, strava_access_token, strava_refresh_token,
                strava_token_expires_at, strava_connected_at, created_at, updated_at
            ) VALUES (1, 'a', 'r', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z',
                      '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        )

    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        with connection.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO account (
                    strava_athlete_id, strava_access_token, strava_refresh_token,
                    strava_token_expires_at, strava_connected_at, created_at, updated_at
                ) VALUES (1, 'b', 'r2', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z',
                          '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
                """
            )
