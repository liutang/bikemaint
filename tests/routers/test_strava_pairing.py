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
