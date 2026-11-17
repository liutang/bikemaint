"""Test-wide defaults so modules that read config at import time (e.g. `app.main`,
which builds the FastAPI app — including the session secret — at module load)
can always be imported during collection, regardless of which test file runs first.

Individual tests override these (e.g. `DATABASE_PATH`) via `monkeypatch` as needed.
"""

import os

os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")
os.environ.setdefault("DATABASE_PATH", ":memory:")

import pytest
from starlette.testclient import TestClient

from app.main import create_app


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return path


@pytest.fixture
def client(db_path):
    app = create_app()
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def signed_in_client(client, monkeypatch):
    """A `TestClient` already signed in through the (stubbed) Strava OAuth callback."""
    from app.services import strava_client

    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 4102444800,
            "athlete": {"id": 42},
        },
    )
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)
    return client


@pytest.fixture
def new_york(db_path):
    """The rider's saved zone is New York (specs/075 tests). Signs in no one; reuses athlete 42."""
    from app.db import accounts, connection
    from app.services import settings_service

    connection.run_migrations()
    with connection.get_connection() as conn:
        account = accounts.get_singleton(conn) or accounts.upsert_from_strava(
            conn, strava_athlete_id=42, access_token="a", refresh_token="r",
            expires_at="2099-01-01T00:00:00.000000Z",
        )
    settings_service.set_timezone(account.id, "America/New_York")
    return account
