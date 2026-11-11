import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/settings"),
        ("post", "/settings/webhook"),
        ("post", "/settings/notifications"),
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
