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
