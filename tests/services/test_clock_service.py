"""Showing UTC-recorded times in the rider's time zone (specs/023-settings-sync-and-timezone, display only)."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.db import accounts, connection
from app.services import clock_service, settings_service


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        return accounts.upsert_from_strava(
            conn, strava_athlete_id=1, access_token="a", refresh_token="r",
            expires_at="2099-01-01T00:00:00.000000Z",
        )


def test_the_zone_is_utc_until_the_rider_chooses_one(account):
    assert clock_service.zone_name() == "UTC"
    assert clock_service.format_utc("2026-01-15T18:00:00.000000Z") == "2026-01-15 18:00 UTC"


def test_a_utc_time_is_shown_in_the_chosen_zone_with_its_abbreviation(account):
    settings_service.set_timezone(account.id, "America/Los_Angeles")

    assert clock_service.format_utc("2026-01-15T18:00:00.000000Z") == "2026-01-15 10:00 PST"


def test_daylight_saving_follows_the_date(account):
    settings_service.set_timezone(account.id, "America/Los_Angeles")

    assert clock_service.format_utc("2026-07-15T18:00:00.000000Z") == "2026-07-15 11:00 PDT"


def test_the_date_can_change_across_midnight(account):
    settings_service.set_timezone(account.id, "Asia/Kolkata")

    assert clock_service.format_utc("2026-01-15T22:00:00.000000Z") == "2026-01-16 03:30 IST"


def test_a_zone_without_a_letter_abbreviation_shows_its_offset(account):
    settings_service.set_timezone(account.id, "Europe/Istanbul")

    assert clock_service.format_utc("2026-01-15T10:00:00.000000Z") == "2026-01-15 13:00 +03"


def test_text_that_is_not_a_time_is_returned_unchanged(account):
    assert clock_service.format_utc("not a time") == "not a time"
    assert clock_service.format_utc(None) == ""


def test_the_setting_is_picked_up_after_a_change_and_separate_databases_do_not_share_it(account, tmp_path, monkeypatch):
    settings_service.set_timezone(account.id, "Europe/London")
    assert clock_service.zone_name() == "Europe/London"

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "other.sqlite3"))
    connection.run_migrations()
    assert clock_service.zone_name() == "UTC"


def test_now_in_the_zone_is_the_zones_wall_clock_in_the_stored_format(account):
    settings_service.set_timezone(account.id, "Pacific/Auckland")

    moment = clock_service.now_in_zone_moment()

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", moment)
    wall = datetime.now(ZoneInfo("Pacific/Auckland")).replace(tzinfo=None)
    assert abs((datetime.strptime(moment, "%Y-%m-%dT%H:%M:%S.%fZ") - wall).total_seconds()) < 5
