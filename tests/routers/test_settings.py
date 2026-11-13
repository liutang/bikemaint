import re

import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/settings"),
        ("post", "/settings/webhook"),
        ("post", "/settings/notifications"),
        ("post", "/settings/strava/sync"),
        ("post", "/settings/timezone"),
    ],
)
def test_settings_routes_redirect_unauthenticated_requests_to_login(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)

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


def test_set_and_remove_webhook_url(client, monkeypatch):
    _login(client, monkeypatch)

    response = client.post(
        "/settings/webhook",
        data={"notification_webhook_url": "https://discord.example/api/webhooks/1/x"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "https://discord.example/api/webhooks/1/x" in client.get("/settings").text

    client.post("/settings/webhook", data={"notification_webhook_url": ""})
    assert "not set" in client.get("/settings").text


def test_webhook_url_must_be_http_or_https(client, monkeypatch):
    _login(client, monkeypatch)

    response = client.post(
        "/settings/webhook", data={"notification_webhook_url": "file:///etc/passwd"}
    )

    assert response.status_code == 422


def test_set_notification_lead_time(client, monkeypatch):
    _login(client, monkeypatch)

    response = client.post(
        "/settings/notifications", data={"notification_lead_time_days": "14"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert "14 days" in client.get("/settings").text


@pytest.mark.parametrize("value", ["-1", "abc", "", "4000"])
def test_invalid_lead_time_is_rejected(client, monkeypatch, value):
    _login(client, monkeypatch)

    response = client.post("/settings/notifications", data={"notification_lead_time_days": value})

    assert response.status_code == 422


# ------------------------------------------------ specs/023: Strava sync panel


def _account_now():
    from app.db import accounts, connection

    with connection.get_connection() as conn:
        return accounts.get_singleton(conn)


def test_the_strava_panel_shows_the_switch_and_the_current_interval(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.delenv("STRAVA_SYNC_INTERVAL_MINUTES", raising=False)

    html = client.get("/settings").text

    assert 'name="sync_enabled"' in html and 'name="interval_hours"' in html and 'name="interval_minutes"' in html
    assert "Every 30 min" in html
    assert re.search(r'<input[^>]*name="sync_enabled"[^>]*\bchecked\b', html)  # on by default


def test_saving_an_interval_stores_it_and_shows_it_back(client, monkeypatch):
    _login(client, monkeypatch)

    response = client.post(
        "/settings/strava/sync",
        data={"sync_enabled": "on", "interval_hours": "1", "interval_minutes": "30"},
        follow_redirects=False,
    )

    assert (response.status_code, response.headers["location"]) == (303, "/settings")
    saved = _account_now()
    assert (saved.strava_sync_enabled, saved.strava_sync_interval_minutes) == (True, 90)
    assert "Every 1 h 30 min" in client.get("/settings").text


def test_turning_sync_off_is_saved_and_shown(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/settings/strava/sync", data={"interval_hours": "0", "interval_minutes": "30"})  # no switch

    assert _account_now().strava_sync_enabled is False
    assert "Automatic sync is off" in client.get("/settings").text


@pytest.mark.parametrize(
    "hours,minutes",
    [("0", "4"), ("0", "0"), ("169", "0"), ("1", "60"), ("x", "5"), ("", "")],
)
def test_a_bad_interval_re_shows_the_page_with_a_message_and_changes_nothing(client, monkeypatch, hours, minutes):
    _login(client, monkeypatch)

    response = client.post(
        "/settings/strava/sync",
        data={"sync_enabled": "on", "interval_hours": hours, "interval_minutes": minutes},
    )

    assert response.status_code == 422
    assert 'class="field-error"' in response.text or 'role="alert"' in response.text
    assert _account_now().strava_sync_interval_minutes is None


def test_the_manual_sync_still_works_when_automatic_sync_is_off(client, monkeypatch):
    from app.services import sync_service

    _login(client, monkeypatch)
    client.post("/settings/strava/sync", data={"interval_hours": "1", "interval_minutes": "0"})
    calls = []
    monkeypatch.setattr(sync_service, "sync_incremental", lambda account_id: calls.append(account_id))

    response = client.post("/sync/strava", follow_redirects=False)

    assert response.status_code == 303 and len(calls) == 1


# ------------------------------------------------ specs/023: time zone


def _timezone_select(html):
    return re.search(r'<select id="timezone".*?</select>', html, re.S).group(0)


def test_the_time_zone_section_is_a_short_offset_dropdown_with_utc_selected_at_first(client, monkeypatch):
    _login(client, monkeypatch)

    html = client.get("/settings").text

    select = _timezone_select(html)
    assert 'name="timezone"' in select and "<datalist" not in html
    assert '<option value="America/Los_Angeles">-08:00 PST</option>' in select
    assert '<option value="America/New_York">-05:00 EST</option>' in select
    assert re.search(r'<option value="UTC" selected>\+00:00 UTC</option>', select)
    assert "America/Argentina" not in html and len(re.findall(r"<option", select)) <= 45


def test_a_zone_saved_earlier_that_is_not_in_the_list_stays_selected(client, monkeypatch):
    _login(client, monkeypatch)
    client.post("/settings/timezone", data={"timezone": "Europe/Istanbul"})

    select = _timezone_select(client.get("/settings").text)

    assert re.search(r'<option value="Europe/Istanbul" selected>Current: \+03:00', select)


def test_saving_a_zone_stores_it_and_shows_connected_since_in_it(client, monkeypatch):
    _login(client, monkeypatch)
    account = _account_now()

    response = client.post("/settings/timezone", data={"timezone": "America/Los_Angeles"}, follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/settings")
    assert _account_now().timezone == "America/Los_Angeles"
    html = client.get("/settings").text
    assert "America/Los_Angeles" in html and re.search(r"since \d{4}-\d\d-\d\d \d\d:\d\d P[SD]T", html)
    assert account.strava_connected_at[:4] in html


@pytest.mark.parametrize("name", ["", "Mars/Olympus", "america/los_angeles"])
def test_an_unknown_zone_is_refused_with_a_message_beside_the_field(client, monkeypatch, name):
    _login(client, monkeypatch)

    response = client.post("/settings/timezone", data={"timezone": name})

    assert response.status_code == 422
    assert 'id="timezone-error"' in response.text
    assert _account_now().timezone == "UTC"


def test_the_current_zone_is_described_by_its_offset_not_a_city(client, monkeypatch):
    _login(client, monkeypatch)
    client.post("/settings/timezone", data={"timezone": "America/New_York"})

    html = client.get("/settings").text

    assert "Currently -05:00 EST." in html
