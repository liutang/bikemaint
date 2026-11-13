import pytest

from app.services import bike_service


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/maintenance/due"),
        ("get", "/bikes/1/schedules/new"),
        ("post", "/bikes/1/schedules"),
        ("get", "/components/1/schedules/new"),
        ("post", "/components/1/schedules"),
        ("get", "/schedules/1/edit"),
        ("post", "/schedules/1"),
        ("post", "/schedules/1/complete"),
        ("post", "/schedules/1/delete"),
        ("post", "/notifications/1/acknowledge"),
    ],
)
def test_schedule_routes_redirect_unauthenticated_requests_to_login(client, method, path):
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


def test_due_dashboard_lists_schedules_across_bikes_and_components(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)
    client.post("/components", data={"name": "Wax Chain", "component_type": "chain"})

    client.post("/bikes/1/schedules", data={"name": "Annual service", "interval_days": "365"})
    client.post("/components/1/schedules", data={"name": "Wax chain", "interval_days": "30"})
    response = client.get("/maintenance/due")

    assert response.status_code == 200
    assert "Annual service" in response.text
    assert "Road Bike" in response.text
    assert "Wax chain" in response.text
    assert "Wax Chain" in response.text


def test_schedule_without_any_interval_is_rejected(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)

    response = client.post("/bikes/1/schedules", data={"name": "No interval"})

    assert response.status_code == 422


def test_schedule_for_unknown_bike_returns_404(client, monkeypatch):
    _login(client, monkeypatch)

    response = client.post("/bikes/999/schedules", data={"name": "X", "interval_days": "30"})

    assert response.status_code == 404


def test_complete_schedule_logs_maintenance_and_returns_to_dashboard(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)
    client.post("/bikes/1/schedules", data={"name": "Annual service", "interval_days": "365"})

    response = client.post("/schedules/1/complete", follow_redirects=False)

    assert response.status_code == 303
    history = client.get("/bikes/1/maintenance")
    assert "Annual service" in history.text


def test_edit_and_delete_schedule(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)
    client.post("/bikes/1/schedules", data={"name": "Old name", "interval_days": "30"})

    form = client.get("/schedules/1/edit")
    assert form.status_code == 200
    assert "Old name" in form.text

    client.post("/schedules/1", data={"name": "New name", "interval_days": "60", "is_active": "on"})
    assert "New name" in client.get("/maintenance/due").text

    client.post("/schedules/1/delete")
    assert "New name" not in client.get("/maintenance/due").text


# ------------------------------------------------ specs/031: Cancel returns where the rider came from


def _signed_in_bike_and_part(signed_in_client):
    from app.services import component_service

    bike = bike_service.create_bike(name="Road Bike")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    return bike, wheel


def test_cancel_on_a_new_part_schedule_returns_to_the_part(signed_in_client):
    bike, wheel = _signed_in_bike_and_part(signed_in_client)

    html = signed_in_client.get(f"/components/{wheel.id}/schedules/new").text

    assert f'<a class="btn" href="/components/{wheel.id}">Cancel</a>' in html


def test_cancel_on_a_new_bike_schedule_returns_to_the_bike(signed_in_client):
    bike, _ = _signed_in_bike_and_part(signed_in_client)

    html = signed_in_client.get(f"/bikes/{bike.id}/schedules/new").text

    assert f'<a class="btn" href="/bikes/{bike.id}">Cancel</a>' in html


def test_cancel_still_returns_to_the_part_after_a_validation_error(signed_in_client):
    _, wheel = _signed_in_bike_and_part(signed_in_client)

    response = signed_in_client.post(f"/components/{wheel.id}/schedules", data={"name": ""})

    assert response.status_code == 422
    assert f'<a class="btn" href="/components/{wheel.id}">Cancel</a>' in response.text


def test_cancel_on_an_existing_schedule_still_returns_to_the_due_page(signed_in_client):
    from app.services import schedule_service

    bike, _ = _signed_in_bike_and_part(signed_in_client)
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Service", interval_days=30)

    html = signed_in_client.get(f"/schedules/{schedule.id}/edit").text

    assert '<a class="btn" href="/maintenance/due">Cancel</a>' in html
