import pytest
from fastapi import Depends
from starlette.testclient import TestClient

from app.db import connection
from app.main import create_app
from app.services.auth_dependency import require_account


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return path


def test_create_app_runs_migrations_on_startup(db_path):
    app = create_app()

    with TestClient(app, base_url="https://testserver"):
        pass

    with connection.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"account", "bike", "component"} <= tables


def test_static_files_are_served(db_path):
    app = create_app()

    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/static/styles.css")

    assert response.status_code == 200


def test_protected_route_redirects_to_login_when_unauthenticated(db_path):
    app = create_app()

    @app.get("/protected-test-route")
    def _protected(account=Depends(require_account)):
        return {"account_id": account.id}

    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/protected-test-route", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


PUBLIC_ROUTE_PATHS = {"/login", "/auth/strava/callback", "/logout"}


def _dependency_calls(dependant):
    yield dependant.call
    for sub in dependant.dependencies:
        yield from _dependency_calls(sub)


def test_every_route_requires_an_account_except_the_public_auth_routes(db_path):
    """FR-021 / Constitution Principle IV: HTMX partials and pages alike are gated."""
    from fastapi.routing import APIRoute

    app = create_app()
    ungated = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path not in PUBLIC_ROUTE_PATHS
        and require_account not in set(_dependency_calls(route.dependant))
    ]

    assert ungated == []


def test_auto_generated_api_docs_are_not_exposed_without_a_session(db_path):
    app = create_app()

    with TestClient(app, base_url="https://testserver") as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path, follow_redirects=False).status_code == 404


def test_session_cookie_is_secure_httponly_and_samesite(db_path, monkeypatch):
    from app.services import strava_client

    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "a",
            "refresh_token": "r",
            "expires_at": 1893456000,
            "athlete": {"id": 1},
        },
    )
    app = create_app()

    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/auth/strava/callback?code=x", follow_redirects=False)

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie


def test_outbound_http_client_logging_does_not_leak_webhook_urls(db_path):
    """httpx logs every request URL at INFO, and webhook URLs embed a secret token."""
    import logging

    create_app()

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
