import httpx
import pytest
import respx

from app.db import accounts, connection
from app.services import strava_client


@pytest.fixture(autouse=True)
def strava_credentials(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


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


@respx.mock
def test_get_athlete_gear_returns_bikes_list():
    respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(
            200, json={"id": 1, "bikes": [{"id": "b123", "name": "Gravel Bike"}]}
        )
    )

    gear = strava_client.get_athlete_gear("access-token")

    assert gear == [{"id": "b123", "name": "Gravel Bike"}]


@respx.mock
def test_get_athlete_gear_sends_bearer_token():
    route = respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(200, json={"bikes": []})
    )

    strava_client.get_athlete_gear("my-token")

    assert route.calls.last.request.headers["Authorization"] == "Bearer my-token"


@respx.mock
def test_get_activities_sends_bearer_token_and_after_cursor():
    route = respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
    )

    activities = strava_client.get_activities("my-token", after=1700000000)

    sent = route.calls.last.request.url.params
    assert sent["after"] == "1700000000"
    assert route.calls.last.request.headers["Authorization"] == "Bearer my-token"
    assert len(activities) == 2


@respx.mock
def test_get_activities_omits_after_cursor_when_not_given():
    route = respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[])
    )

    strava_client.get_activities("my-token")

    assert "after" not in route.calls.last.request.url.params


@respx.mock
def test_get_activities_follows_pages_until_a_short_page():
    full = [{"id": i} for i in range(200)]
    route = respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        side_effect=[
            httpx.Response(200, json=full),
            httpx.Response(200, json=full),
            httpx.Response(200, json=[{"id": 999}]),
        ]
    )

    activities = strava_client.get_activities("my-token")

    assert len(activities) == 401
    pages = [c.request.url.params["page"] for c in route.calls]
    assert pages == ["1", "2", "3"]


@respx.mock
def test_get_activities_stops_when_first_page_is_empty():
    route = respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[])
    )

    assert strava_client.get_activities("my-token") == []
    assert route.call_count == 1


def _create_account(expires_at: str) -> accounts.Account:
    with connection.get_connection() as conn:
        return accounts.upsert_from_strava(
            conn,
            strava_athlete_id=42,
            access_token="old-access-token",
            refresh_token="old-refresh-token",
            expires_at=expires_at,
        )


def test_ensure_fresh_access_token_reuses_unexpired_token_without_a_refresh_call(db_path):
    account = _create_account(expires_at="2099-01-01T00:00:00.000000Z")

    with respx.mock:
        # No route registered: any HTTP call here would raise, proving no refresh happened.
        token = strava_client.ensure_fresh_access_token(account)

    assert token == "old-access-token"


@respx.mock
def test_ensure_fresh_access_token_refreshes_and_persists_when_expired(db_path):
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_at": 1893456000,
            },
        )
    )
    account = _create_account(expires_at="2020-01-01T00:00:00.000000Z")

    token = strava_client.ensure_fresh_access_token(account)

    assert token == "new-access-token"
    with connection.get_connection() as conn:
        refreshed = accounts.get_by_id(conn, account.id)
    assert refreshed.strava_access_token == "new-access-token"
    assert refreshed.strava_connection_stale is False


@respx.mock
def test_ensure_fresh_access_token_marks_account_stale_on_refresh_failure(db_path):
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    account = _create_account(expires_at="2020-01-01T00:00:00.000000Z")

    with pytest.raises(strava_client.StravaTokenRefreshError):
        strava_client.ensure_fresh_access_token(account)

    with connection.get_connection() as conn:
        refreshed = accounts.get_by_id(conn, account.id)
    assert refreshed.strava_connection_stale is True


# ------------------------------------------------ gear needs profile access (specs: Strava gear scope)


@respx.mock
def test_missing_bikes_key_means_strava_did_not_share_gear():
    # Without the profile:read_all scope Strava omits `bikes` from the athlete entirely.
    respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(200, json={"id": 1, "firstname": "Sam"})
    )

    with pytest.raises(strava_client.StravaGearAccessError):
        strava_client.get_athlete_gear("access-token")


@respx.mock
def test_null_bikes_is_treated_the_same_way():
    respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(200, json={"id": 1, "bikes": None})
    )

    with pytest.raises(strava_client.StravaGearAccessError):
        strava_client.get_athlete_gear("access-token")


@respx.mock
def test_an_athlete_with_no_bikes_is_an_empty_list_not_an_error():
    respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(200, json={"id": 1, "bikes": []})
    )

    assert strava_client.get_athlete_gear("access-token") == []


@respx.mock
def test_get_activities_allows_slow_strava_responses():
    route = respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[])
    )

    strava_client.get_activities("token")

    assert route.calls.last.request.extensions["timeout"]["read"] >= 30


# ------------------------------------------------ specs/017 remediation R1 and R2


@respx.mock
def test_a_timeout_fetching_activities_becomes_a_domain_error():
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        side_effect=httpx.ReadTimeout("The read operation timed out")
    )

    with pytest.raises(strava_client.StravaUnavailableError):
        strava_client.get_activities("token")


@respx.mock
def test_a_strava_server_error_fetching_activities_becomes_a_domain_error():
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(503)
    )

    with pytest.raises(strava_client.StravaUnavailableError):
        strava_client.get_activities("token")


@respx.mock
def test_missing_gear_list_is_logged_without_the_token(caplog):
    respx.get("https://www.strava.com/api/v3/athlete").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )

    with caplog.at_level("WARNING"), pytest.raises(strava_client.StravaGearAccessError):
        strava_client.get_athlete_gear("secret-access-token")

    assert "gear list" in caplog.text and "profile:read_all" in caplog.text
    assert "secret-access-token" not in caplog.text
