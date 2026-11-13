"""Router test for the not-yet-implemented mileage/pairing routes (User Story 2).

Written ahead of the implementation per the constitution's TDD mandate
(Principle III) — expect these to fail (404, routes not registered yet) until
T043/T044 land.
"""

import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/bikes/1/strava-pairing"),
        ("post", "/bikes/1/strava-pairing"),
        ("post", "/sync/strava"),
    ],
)
def test_mileage_routes_redirect_unauthenticated_requests_to_login(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


# ------------------------------------------------ specs/003 FR-006a


def test_the_top_bar_says_synced_just_now_after_a_sync_that_found_nothing(signed_in_client, monkeypatch):
    from app.services import strava_client

    monkeypatch.setattr(strava_client, "get_activities", lambda access_token, **kwargs: [])
    assert "Not synced yet" in signed_in_client.get("/").text

    signed_in_client.post("/sync/strava", follow_redirects=False)

    assert "Synced just now" in signed_in_client.get("/").text
