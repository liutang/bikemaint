import httpx
import pytest
import respx

from app.services import strava_client


@pytest.fixture(autouse=True)
def strava_credentials(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")


@respx.mock
def test_exchange_code_for_token_posts_authorization_code_grant():
    route = respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_at": 1893456000,
                "athlete": {"id": 42},
            },
        )
    )

    result = strava_client.exchange_code_for_token("auth-code")

    assert route.calls.last.request.method == "POST"
    sent = httpx.QueryParams(route.calls.last.request.content.decode())
    assert sent["client_id"] == "test-client-id"
    assert sent["client_secret"] == "test-client-secret"
    assert sent["code"] == "auth-code"
    assert sent["grant_type"] == "authorization_code"
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"
    assert result["athlete"]["id"] == 42


@respx.mock
def test_exchange_code_for_token_raises_on_error_response():
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(400, json={"message": "Bad Request"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        strava_client.exchange_code_for_token("bad-code")


@respx.mock
def test_refresh_access_token_posts_refresh_token_grant():
    route = respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_at": 1893456000,
            },
        )
    )

    result = strava_client.refresh_access_token("old-refresh-token")

    sent = httpx.QueryParams(route.calls.last.request.content.decode())
    assert sent["refresh_token"] == "old-refresh-token"
    assert sent["grant_type"] == "refresh_token"
    assert result["access_token"] == "new-access-token"
    assert result["refresh_token"] == "new-refresh-token"


@respx.mock
def test_refresh_access_token_raises_on_error_response():
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        strava_client.refresh_access_token("revoked-refresh-token")
