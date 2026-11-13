import pytest

from app.services import bike_service


@pytest.mark.parametrize(
    "method,path,data",
    [
        ("get", "/components", None),
        ("get", "/components/new", None),
        ("post", "/components", {"name": "Tire", "component_type": "tire"}),
        ("get", "/components/1", None),
        ("get", "/components/1/edit", None),
        ("post", "/components/1", {"name": "Tire", "component_type": "tire"}),
        ("post", "/components/1/move", {}),
        ("post", "/components/1/delete", {}),
    ],
)
def test_component_routes_redirect_unauthenticated_requests_to_login(
    client, method, path, data
):
    kwargs = {"data": data} if method == "post" else {}
    response = getattr(client, method)(path, follow_redirects=False, **kwargs)

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


def test_in_storage_list_shows_unattached_components(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/components", data={"name": "Spare Tire", "component_type": "tire"})
    response = client.get("/components")

    assert response.status_code == 200
    assert "Spare Tire" in response.text


def test_create_component_allows_a_second_part_of_the_same_kind_under_one_parent(
    client, monkeypatch
):
    _login(client, monkeypatch)

    bike_service.create_bike(name="Commuter", manual_baseline_mileage=0)

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Commuter'").fetchone()["id"]

    first = client.post(
        "/components",
        data={"name": "Frame", "component_type": "frame", "parent_bike_id": str(bike_id)},
    )
    assert first.status_code in (200, 303)

    second = client.post(
        "/components",
        data={"name": "Second Frame", "component_type": "frame", "parent_bike_id": str(bike_id)},
    )
    assert second.status_code in (200, 303)


def test_move_component_to_storage(client, monkeypatch):
    _login(client, monkeypatch)

    bike_service.create_bike(name="Commuter", manual_baseline_mileage=0)

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Commuter'").fetchone()["id"]

    client.post(
        "/components",
        data={"name": "Wheel", "component_type": "wheel", "parent_bike_id": str(bike_id)},
    )
    with connection.get_connection() as conn:
        component_id = conn.execute(
            "SELECT id FROM component WHERE name = 'Wheel'"
        ).fetchone()["id"]

    response = client.post(f"/components/{component_id}/move", data={})

    assert response.status_code in (200, 303)

    with connection.get_connection() as conn:
        row = conn.execute(
            "SELECT parent_bike_id, parent_component_id FROM component WHERE id = ?",
            (component_id,),
        ).fetchone()
    assert row["parent_bike_id"] is None
    assert row["parent_component_id"] is None
