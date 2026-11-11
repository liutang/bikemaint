import pytest

from app.services import bike_service


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/bikes/1/maintenance"),
        ("get", "/bikes/1/maintenance/new"),
        ("post", "/bikes/1/maintenance"),
        ("get", "/components/1/maintenance"),
        ("get", "/components/1/maintenance/new"),
        ("post", "/components/1/maintenance"),
        ("get", "/maintenance/1/edit"),
        ("post", "/maintenance/1"),
        ("post", "/maintenance/1/delete"),
    ],
)
def test_maintenance_routes_redirect_unauthenticated_requests_to_login(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _login(client, monkeypatch, athlete_id=42):
    from app.services import bike_service, strava_client

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
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)


def test_log_then_view_bike_maintenance_history(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=50)

    response = client.post(
        "/bikes/1/maintenance",
        data={"description": "Replaced brake pads", "performed_at": "2026-05-01"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/bikes/1/maintenance"

    history = client.get("/bikes/1/maintenance")
    assert history.status_code == 200
    assert "Replaced brake pads" in history.text
    assert "2026-05-01" in history.text


def test_invalid_maintenance_entry_returns_422(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)

    response = client.post(
        "/bikes/1/maintenance", data={"description": "", "performed_at": "not-a-date"}
    )

    assert response.status_code == 422


def test_edit_and_delete_maintenance_entry(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)
    client.post(
        "/bikes/1/maintenance", data={"description": "Old", "performed_at": "2026-05-01"}
    )

    edit = client.post(
        "/maintenance/1",
        data={
            "description": "New",
            "performed_at": "2026-05-02",
            "mileage_at_service": "10",
        },
        follow_redirects=False,
    )
    assert edit.status_code == 303
    assert "New" in client.get("/bikes/1/maintenance").text

    deleted = client.post("/maintenance/1/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert "New" not in client.get("/bikes/1/maintenance").text


def test_component_maintenance_history_route(client, monkeypatch):
    _login(client, monkeypatch)
    client.post("/components", data={"name": "Chain", "component_type": "chain"})

    client.post(
        "/components/1/maintenance",
        data={"description": "Waxed chain", "performed_at": "2026-05-01"},
    )

    response = client.get("/components/1/maintenance")
    assert response.status_code == 200
    assert "Waxed chain" in response.text


def test_maintenance_for_unknown_bike_returns_404(client, monkeypatch):
    _login(client, monkeypatch)

    assert client.get("/bikes/999/maintenance").status_code == 404
