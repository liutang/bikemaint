import pytest


@pytest.mark.parametrize(
    "method,path,data",
    [
        ("get", "/", None),
        ("get", "/bikes/1", None),
        ("get", "/bikes/new", None),
        ("post", "/bikes", {"name": "Test Bike", "manual_baseline_mileage": "0"}),
        ("get", "/bikes/1/edit", None),
        ("post", "/bikes/1", {"name": "Test Bike", "manual_baseline_mileage": "0"}),
        ("post", "/bikes/1/delete", {}),
    ],
)
def test_bike_routes_redirect_unauthenticated_requests_to_login(client, method, path, data):
    kwargs = {"data": data} if method == "post" else {}
    response = getattr(client, method)(path, follow_redirects=False, **kwargs)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _login(client, monkeypatch, athlete_id=42):
    from app.services import strava_client

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


def test_garage_overview_lists_created_bikes(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"name": "Gravel Bike", "manual_baseline_mileage": "0"})
    response = client.get("/")

    assert response.status_code == 200
    assert "Gravel Bike" in response.text


def test_create_then_view_bike_detail(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"name": "Road Bike", "manual_baseline_mileage": "10"})

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Road Bike'").fetchone()["id"]

    response = client.get(f"/bikes/{bike_id}")

    assert response.status_code == 200
    assert "Road Bike" in response.text


def test_delete_bike_with_installed_component_returns_confirmation_fragment(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"name": "Commuter", "manual_baseline_mileage": "0"})

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Commuter'").fetchone()["id"]

    client.post(
        "/components",
        data={"name": "Wheel", "component_type": "wheel", "parent_bike_id": str(bike_id)},
    )

    response = client.post(f"/bikes/{bike_id}/delete", data={})

    assert response.status_code == 200
    assert "onfirm" in response.text

    response = client.post(f"/bikes/{bike_id}/delete", data={"confirmed": "true"})
    assert response.status_code in (200, 303)

    with connection.get_connection() as conn:
        row = conn.execute("SELECT is_deleted FROM bike WHERE id = ?", (bike_id,)).fetchone()
    assert row["is_deleted"] == 1
