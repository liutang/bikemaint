"""End-to-end walkthrough of specs/001-bike-maintenance-tracker/quickstart.md (T079).

Drives the real app through HTTP with Strava (and the outbound webhook) mocked, following
each quickstart scenario in order. Strava's OAuth sign-in itself can't be exercised without
real credentials, so the login step stubs the token exchange.
"""

import json
from datetime import date

import httpx
import pytest
import respx

from app.db import connection
from app.services import (
    bike_service,
    notification_service,
    schedule_service,
    strava_client,
)

WEBHOOK_URL = "https://discord.example/api/webhooks/1/token"


@pytest.fixture
def signed_in(client, monkeypatch):
    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 4102444800,  # 2100-01-01
            "athlete": {"id": 7},
        },
    )
    client.get("/auth/strava/callback?code=code", follow_redirects=False)
    return client


def _add_bike(client, name):
    bike_service.create_bike(name=name, manual_baseline_mileage=0)


def _add_component(client, name, component_type, **parent):
    return client.post(
        "/components",
        data={"name": name, "component_type": component_type, **parent},
        follow_redirects=False,
    )


def test_scenario_1_garage_inventory(signed_in):
    client = signed_in
    _add_bike(client, "Gravel Bike")
    _add_bike(client, "Road Bike")
    assert "Gravel Bike" in client.get("/").text

    _add_component(client, "Gravel Wheel", "wheel", parent_bike_id="1")
    _add_component(client, "Gravel Tire", "tire", parent_component_id="1")
    detail = client.get("/bikes/1").text
    assert detail.index("Gravel Wheel") < detail.index("Gravel Tire")

    client.post("/components/2/move", data={})
    assert "Gravel Tire" in client.get("/components").text
    assert "Gravel Tire" not in client.get("/bikes/1").text

    _add_component(client, "Road Wheel", "wheel", parent_bike_id="2")
    client.post("/components/2/move", data={"parent_component_id": "3"})
    assert "Gravel Tire" in client.get("/bikes/2").text
    assert "Gravel Tire" not in client.get("/components").text

    # Cross-cutting: a second single-instance tire on an occupied wheel is rejected (FR-024).
    duplicate = _add_component(client, "Second Tire", "tire", parent_component_id="3")
    assert duplicate.status_code == 422


def test_scenario_2_strava_sync_adjustment_and_stale_connection(signed_in, monkeypatch):
    client = signed_in
    _add_bike(client, "Gravel Bike")
    _add_component(client, "Wheel", "wheel", parent_bike_id="1")

    monkeypatch.setattr(
        strava_client, "get_athlete_gear", lambda token: [{"id": "g1", "name": "Gravel"}]
    )
    assert "Gravel" in client.get("/bikes/1/strava-pairing").text

    history = [
        {"id": 1, "gear_id": "g1", "distance": 16093.4, "start_date": "2026-01-01T08:00:00Z"}
    ]
    monkeypatch.setattr(strava_client, "get_activities", lambda token, **kw: history)
    paired = client.post(
        "/bikes/1/strava-pairing", data={"strava_gear_id": "g1"}, follow_redirects=False
    )
    assert paired.status_code == 303
    assert bike_service.get_bike(1).total_mileage == pytest.approx(10.0, abs=0.01)
    # Once paired, that gear no longer appears as an option.
    assert "No unpaired Strava gear" in client.get("/bikes/1/strava-pairing").text

    # A ride after the wheel was installed credits both; the earlier one credited only the bike.
    history.append(
        {"id": 2, "gear_id": "g1", "distance": 32186.8, "start_date": "2099-01-01T08:00:00Z"}
    )
    assert client.post("/sync/strava", follow_redirects=False).status_code == 303
    assert bike_service.get_bike(1).total_mileage == pytest.approx(30.0, abs=0.01)
    assert "20.0 mi" in client.get("/components/1").text

    client.post("/bikes/1/mileage/adjust", data={"delta_miles": "-5", "reason": "Wrong ride"})
    assert bike_service.get_bike(1).total_mileage == pytest.approx(25.0, abs=0.01)

    # Revoked access: token expired and refresh rejected -> connection goes stale, data stays.
    with connection.get_connection() as conn:
        conn.execute("UPDATE account SET strava_token_expires_at = '2000-01-01T00:00:00.000000Z'")
    with respx.mock:
        respx.post("https://www.strava.com/oauth/token").mock(return_value=httpx.Response(400))
        client.post("/sync/strava", follow_redirects=False)
    assert "stale" in client.get("/settings").text.lower()
    assert bike_service.get_bike(1).total_mileage == pytest.approx(25.0, abs=0.01)


def test_scenario_3_maintenance_log_follows_the_component(signed_in):
    client = signed_in
    _add_bike(client, "Bike A")
    _add_bike(client, "Bike B")
    _add_component(client, "Chain", "chain", parent_bike_id="1")

    client.post("/components/1/maintenance", data={"description": "Waxed", "performed_at": "2026-05-01"})
    assert "Waxed" in client.get("/components/1/maintenance").text

    client.post("/components/1/move", data={"parent_bike_id": "2"})
    assert "Waxed" in client.get("/components/1/maintenance").text
    assert "Waxed" not in client.get("/bikes/1/maintenance").text

    client.post(
        "/maintenance/1",
        data={"description": "Waxed and checked", "performed_at": "2026-05-02"},
    )
    assert "Waxed and checked" in client.get("/components/1/maintenance").text
    client.post("/maintenance/1/delete")
    assert "Waxed" not in client.get("/components/1/maintenance").text


@respx.mock
def test_scenario_4_schedules_notifications_and_completion(signed_in, monkeypatch):
    client = signed_in
    monkeypatch.setattr(notification_service, "_sleep", lambda seconds: None)
    _add_bike(client, "Gravel Bike")
    _add_component(client, "Chain", "chain", parent_bike_id="1")
    webhook = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(204))

    client.post("/settings/webhook", data={"notification_webhook_url": WEBHOOK_URL})
    client.post("/settings/notifications", data={"notification_lead_time_days": "30"})

    # Brand-new setup with only a mileage interval: no misleading date, flagged low confidence.
    client.post("/components/1/schedules", data={"name": "Replace chain", "interval_miles": "1500"})
    dashboard = client.get("/maintenance/due").text
    assert "Replace chain" in dashboard
    assert "low confidence" in dashboard.lower()

    # A time-interval schedule inside the lead-time window notifies exactly once per cycle.
    client.post("/bikes/1/schedules", data={"name": "Annual service", "interval_days": "10"})
    notification_service.check_due_schedules()
    notification_service.check_due_schedules()
    assert webhook.call_count == 1
    payload = json.loads(webhook.calls[0].request.content)
    assert payload["schedule"]["name"] == "Annual service"
    assert "Annual service" in client.get("/maintenance/due").text

    # Completing logs maintenance and starts the next cycle.
    client.post("/schedules/2/complete", follow_redirects=False)
    assert "Annual service" in client.get("/bikes/1/maintenance").text
    assert schedule_service.get_schedule(2).cycle_number == 2
    assert schedule_service.get_schedule(2).baseline_date == date.today().isoformat()


def test_cross_cutting_unauthenticated_and_delete_confirmation(client, monkeypatch):
    for path in ("/", "/components", "/maintenance/due", "/settings", "/bikes/1/maintenance"):
        response = client.get(path, follow_redirects=False)
        assert (response.status_code, response.headers["location"]) == (303, "/login")

    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "a",
            "refresh_token": "r",
            "expires_at": 4102444800,
            "athlete": {"id": 7},
        },
    )
    client.get("/auth/strava/callback?code=code", follow_redirects=False)
    _add_bike(client, "Gravel Bike")
    client.post("/bikes/1/schedules", data={"name": "Service", "interval_days": "30"})

    # FR-020: a bike with an active schedule needs confirmation before it is deleted.
    first = client.post("/bikes/1/delete", data={}, follow_redirects=False)
    assert first.status_code == 200
    assert "Yes, delete" in first.text
    assert bike_service.get_bike(1) is not None

    client.post("/bikes/1/delete", data={"confirmed": "true"})
    assert bike_service.get_bike(1) is None
