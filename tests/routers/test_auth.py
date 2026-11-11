import pytest
from fastapi import Depends
from starlette.testclient import TestClient

from app.db import connection
from app.main import create_app
from app.services import strava_client
from app.services.auth_dependency import require_account


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return path


@pytest.fixture
def client(db_path):
    app = create_app()

    @app.get("/protected-test-route")
    def _protected(account=Depends(require_account)):
        return {"account_id": account.id}

    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def _stub_token_exchange(monkeypatch, athlete_id: int = 42):
    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 1893456000,
            "athlete": {"id": athlete_id},
        },
    )


def test_login_page_renders_strava_authorize_link(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "Sign in with Strava" in response.text
    assert "https://www.strava.com/oauth/authorize" in response.text
    assert "client_id=test-client-id" in response.text
    assert "scope=profile%3Aread_all%2Cactivity%3Aread_all" in response.text  # profile access lists gear


def test_strava_callback_upserts_account_and_establishes_session(client, monkeypatch):
    _stub_token_exchange(monkeypatch)

    response = client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session" in response.cookies

    with connection.get_connection() as conn:
        row = conn.execute("SELECT strava_athlete_id FROM account").fetchone()
    assert row["strava_athlete_id"] == 42


def test_protected_route_unreachable_before_login(client):
    response = client.get("/protected-test-route", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logged_in_session_reaches_protected_route(client, monkeypatch):
    _stub_token_exchange(monkeypatch)
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)

    response = client.get("/protected-test-route")

    assert response.status_code == 200
    assert response.json()["account_id"] is not None


def test_logout_clears_session_and_redirects_to_login(client, monkeypatch):
    _stub_token_exchange(monkeypatch)
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)

    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    protected_response = client.get("/protected-test-route", follow_redirects=False)
    assert protected_response.status_code == 303
    assert protected_response.headers["location"] == "/login"


# ------------------------------------------------ behind a reverse proxy (specs/009)

from urllib.parse import parse_qs, urlparse  # noqa: E402


def _redirect_uri(html: str) -> str:
    import html as html_lib
    import re

    href = html_lib.unescape(re.search(r'href="(https://www\.strava\.com/oauth/authorize[^"]+)"', html).group(1))
    return parse_qs(urlparse(href).query)["redirect_uri"][0]


def test_the_redirect_address_follows_the_request_by_default(client):
    assert _redirect_uri(client.get("/login").text) == "https://testserver/auth/strava/callback"


def test_a_public_base_url_overrides_the_redirect_address(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bikemaint.hosts.the-tangs.com")

    assert _redirect_uri(client.get("/login").text) == "https://bikemaint.hosts.the-tangs.com/auth/strava/callback"


def test_a_trailing_slash_in_the_public_base_url_is_tolerated(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bikemaint.hosts.the-tangs.com/")

    assert _redirect_uri(client.get("/login").text) == "https://bikemaint.hosts.the-tangs.com/auth/strava/callback"


@pytest.mark.parametrize("bad", ["", "   ", "javascript:alert(1)", "ftp://x", "not a url"])
def test_an_unusable_public_base_url_is_ignored(client, monkeypatch, bad):
    monkeypatch.setenv("PUBLIC_BASE_URL", bad)

    assert _redirect_uri(client.get("/login").text) == "https://testserver/auth/strava/callback"
