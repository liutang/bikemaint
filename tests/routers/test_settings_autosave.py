"""Settings cards save themselves (specs/071-ui-consistency US2)."""

import re

import pytest

from app.services import settings_service

HX = {"HX-Request": "true"}


def _account(client):
    from app.db import accounts, connection
    with connection.get_connection() as conn:
        return accounts.get_singleton(conn)


def test_settings_has_no_save_buttons_and_every_card_form_saves_on_change(signed_in_client):
    html = signed_in_client.get("/settings").text
    main = html.split("<main")[1]

    for action in ("/settings/theme", "/settings/strava/sync", "/settings/webhook", "/settings/notifications/mute",
                   "/settings/notifications", "/settings/timezone", "/settings/clock"):
        form = re.search(rf'<form[^>]*hx-post="{re.escape(action)}"[^>]*>', main)
        assert form, action
        assert 'hx-trigger="change"' in form.group(0) and 'hx-target="closest .panel"' in form.group(0)
    visible = re.sub(r"<noscript>.*?</noscript>", "", main, flags=re.S)
    assert not re.search(r">\s*Save( [a-z ]+)?\s*</button>", visible)
    assert "<noscript>" in main  # a Save button still appears without scripting


def test_cards_sit_in_a_grid_and_the_webhook_url_is_not_repeated(signed_in_client):
    signed_in_client.post("/settings/webhook", data={"notification_webhook_url": "https://example.com/hook/SECRET"})

    html = signed_in_client.get("/settings").text

    assert 'class="card-grid"' in html and 'class="panel wide" aria-labelledby="webhook-heading"' in html
    assert html.count("https://example.com/hook/SECRET") == 1  # only in the field


@pytest.mark.parametrize("path,data,check", [
    ("/settings/notifications", {"notification_lead_time_days": "11"}, lambda a: a.notification_lead_time_days == 11),
    ("/settings/clock", {"clock_format": "24"}, lambda a: a.clock_format == "24"),
    ("/settings/timezone", {"timezone": "America/Chicago"}, lambda a: a.timezone == "America/Chicago"),
    ("/settings/notifications/mute", {"notifications_muted": "on"}, lambda a: a.notifications_muted),
    ("/settings/strava/sync", {"sync_enabled": "on", "interval_hours": "1", "interval_minutes": "15"},
     lambda a: a.strava_sync_interval_minutes == 75),
    ("/settings/webhook", {"notification_webhook_url": "https://example.com/h"}, lambda a: a.notification_webhook_url == "https://example.com/h"),
])
def test_an_htmx_change_saves_and_returns_just_that_card_saying_saved(signed_in_client, path, data, check):
    response = signed_in_client.post(path, data=data, headers=HX)

    assert response.status_code == 200
    assert response.text.lstrip().startswith("<section") and "<html" not in response.text
    assert re.search(r'class="save-status is-saved"[^>]*>\s*Saved', response.text)
    assert check(_account(signed_in_client))


def test_a_refused_change_says_not_saved_with_the_reason_and_keeps_the_stored_value(signed_in_client):
    response = signed_in_client.post("/settings/notifications", data={"notification_lead_time_days": "-3"}, headers=HX)

    assert response.status_code == 200  # HTMX swaps 2xx answers only
    assert "is-error" in response.text and "Not saved" in response.text
    assert 'id="notification_lead_time_days-error"' in response.text
    assert _account(signed_in_client).notification_lead_time_days == 7


def test_the_card_shows_the_new_value_in_its_description(signed_in_client):
    html = signed_in_client.post("/settings/notifications", data={"notification_lead_time_days": "12"}, headers=HX).text

    assert "Currently 12 days, 20 miles, 2 rides or 2 hours, whichever comes first." in html  # specs/086


def test_the_theme_change_reloads_the_page_so_the_theme_applies(signed_in_client):
    response = signed_in_client.post("/settings/theme", data={"theme": "dark"}, headers=HX)

    assert response.headers.get("HX-Refresh") == "true" and "theme=dark" in response.headers["set-cookie"]


def test_without_htmx_the_routes_still_redirect(signed_in_client):
    response = signed_in_client.post("/settings/clock", data={"clock_format": "24"}, follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/settings")


def test_backup_is_three_cards(signed_in_client, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    signed_in_client.post("/settings/backup/run")

    html = signed_in_client.get("/settings").text

    for heading in ("backup-heading", "restore-heading", "auto-backup-heading"):
        assert f'aria-labelledby="{heading}"' in html
    assert 'class="backup-files"' in html and "today" in html
    assert re.search(r'class="btn btn-primary"[^>]*href="/settings/backup"|href="/settings/backup"[^>]*class="btn btn-primary"', html)
