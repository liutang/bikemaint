"""Pairing a bike with Strava gear (specs: Strava gear scope)."""

import re

import pytest

from app.services import bike_service, strava_client


def _bike():
    return bike_service.create_bike_from_details(year=2023, make="Trek", model="Madone", category="road")


def _gear(monkeypatch, gear=None, error=None):
    def fake(token):
        if error:
            raise error
        return gear

    monkeypatch.setattr(strava_client, "get_athlete_gear", fake)
    monkeypatch.setattr(strava_client, "ensure_fresh_access_token", lambda account: "token")


def test_gear_choices_show_the_strava_names_not_their_ids(signed_in_client, monkeypatch):
    bike = _bike()
    _gear(monkeypatch, [{"id": "b123", "name": "Madone SLR"}, {"id": "b456", "name": "Old commuter"}])

    html = signed_in_client.get(f"/bikes/{bike.id}/strava-pairing").text

    assert re.search(r'<option value="b123">Madone SLR</option>', html)
    assert re.search(r'<option value="b456">Old commuter</option>', html)


def test_missing_profile_access_explains_how_to_fix_it(signed_in_client, monkeypatch):
    bike = _bike()
    _gear(monkeypatch, error=strava_client.StravaGearAccessError("no bikes key"))

    html = signed_in_client.get(f"/bikes/{bike.id}/strava-pairing").text

    assert "Strava did not share your gear list" in html
    assert "profile" in html.lower() and "sign in" in html.lower()
    assert re.search(r'<form[^>]*method="post"[^>]*action="/logout"', html)  # reconnect in one click
    assert "No unpaired Strava gear found" not in html


def test_no_bikes_in_strava_points_at_strava_gear_settings(signed_in_client, monkeypatch):
    bike = _bike()
    _gear(monkeypatch, [])

    html = signed_in_client.get(f"/bikes/{bike.id}/strava-pairing").text

    assert "No unpaired Strava gear found" in html
    assert "strava.com/settings/gear" in html


def test_every_bike_already_paired_still_explains_itself(signed_in_client, monkeypatch):
    bike = _bike()
    other = bike_service.create_bike_from_details(year=2020, make="Giant", model="TCR", category="road")
    bike_service.pair_to_strava_gear  # noqa: B018 (exists)
    from app.db import connection

    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET strava_gear_id = 'b123' WHERE id = ?", (other.id,))
    _gear(monkeypatch, [{"id": "b123", "name": "Giant TCR"}])

    html = signed_in_client.get(f"/bikes/{bike.id}/strava-pairing").text

    assert "No unpaired Strava gear found" in html


def test_a_stale_token_keeps_the_existing_message(signed_in_client, monkeypatch):
    bike = _bike()
    _gear(monkeypatch, error=strava_client.StravaTokenRefreshError("revoked"))

    html = signed_in_client.get(f"/bikes/{bike.id}/strava-pairing").text

    assert "No unpaired Strava gear found" in html and "Strava did not share" not in html


def _paired_bike(monkeypatch):
    bike = _bike()
    monkeypatch.setattr("app.services.sync_service.backfill_bike", lambda bike_id: None)
    return bike_service.pair_to_strava_gear(bike.id, "b123")


def test_paired_bike_offers_reimport_and_unpaired_does_not(signed_in_client, monkeypatch):
    unpaired = _bike()
    assert "Re-import Strava history" not in signed_in_client.get(f"/bikes/{unpaired.id}").text

    paired = _paired_bike(monkeypatch)
    html = signed_in_client.get(f"/bikes/{paired.id}").text

    assert "Re-import Strava history" in html
    assert re.search(rf'<form[^>]*method="post"[^>]*action="/bikes/{paired.id}/strava-reimport"', html)


def test_reimport_runs_the_backfill_and_returns_to_the_bike(signed_in_client, monkeypatch):
    paired = _paired_bike(monkeypatch)
    calls = []
    monkeypatch.setattr("app.services.sync_service.backfill_bike", lambda bike_id: calls.append(bike_id))

    response = signed_in_client.post(f"/bikes/{paired.id}/strava-reimport", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/bikes/{paired.id}"
    assert calls == [paired.id]


def test_reimport_on_an_unpaired_bike_is_rejected(signed_in_client):
    bike = _bike()

    response = signed_in_client.post(f"/bikes/{bike.id}/strava-reimport", follow_redirects=False)

    assert response.status_code == 409


def test_paired_bike_offers_unpair(signed_in_client, monkeypatch):
    paired = _paired_bike(monkeypatch)
    html = signed_in_client.get(f"/bikes/{paired.id}").text
    assert re.search(rf'<form[^>]*method="post"[^>]*action="/bikes/{paired.id}/strava-unpair"', html)


def test_unpair_clears_the_gear_but_keeps_the_rides(signed_in_client, monkeypatch):
    from app.db import connection, mileage

    paired = _paired_bike(monkeypatch)
    with connection.get_connection() as conn:
        mileage.upsert_ride_activity(
            conn, strava_activity_id=1, strava_gear_id="b123", bike_id=paired.id,
            distance_miles=10.0, occurred_at="2024-01-01T10:00:00.000000Z",
        )

    response = signed_in_client.post(f"/bikes/{paired.id}/strava-unpair", follow_redirects=False)

    assert response.status_code == 303
    bike = bike_service.get_bike(paired.id)
    assert bike.strava_gear_id is None and bike.strava_paired_at is None
    with connection.get_connection() as conn:
        assert len(mileage.list_rides_for_bike(conn, paired.id)) == 1
    assert "Pair with Strava" in signed_in_client.get(f"/bikes/{paired.id}").text


def test_unpair_on_an_unpaired_bike_is_rejected(signed_in_client):
    bike = _bike()
    assert signed_in_client.post(f"/bikes/{bike.id}/strava-unpair", follow_redirects=False).status_code == 409


def test_reimport_reports_a_strava_timeout_instead_of_crashing(signed_in_client, monkeypatch):
    from app.services import strava_client

    paired = _paired_bike(monkeypatch)

    def slow(bike_id):
        raise strava_client.StravaUnavailableError("Strava did not answer")

    monkeypatch.setattr("app.services.sync_service.backfill_bike", slow)

    response = signed_in_client.post(f"/bikes/{paired.id}/strava-reimport", follow_redirects=False)

    assert response.status_code == 502
    assert "Strava" in response.text and "try again" in response.text.lower()


# ------------------------------------------------ specs/017 analysis: FR-011 and FR-013


@pytest.mark.parametrize("action", ["strava-reimport", "strava-unpair"])
def test_pairing_actions_on_an_unknown_bike_return_not_found(signed_in_client, action):
    response = signed_in_client.post(f"/bikes/99999/{action}", follow_redirects=False)

    assert response.status_code == 404


@pytest.mark.parametrize("action", ["strava-reimport", "strava-unpair"])
def test_pairing_actions_require_sign_in(client, action):
    response = client.post(f"/bikes/1/{action}", follow_redirects=False)

    assert response.status_code in (302, 303, 401)
    assert "/login" in response.headers.get("location", "") or response.status_code == 401
