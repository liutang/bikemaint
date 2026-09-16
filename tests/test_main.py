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
