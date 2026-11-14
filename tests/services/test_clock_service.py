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
    assert clock_service.format_utc("2026-01-15T18:00:00.000000Z") == "2026-01-15 6:00PM UTC"


def test_a_utc_time_is_shown_in_the_chosen_zone_with_its_abbreviation(account):
    settings_service.set_timezone(account.id, "America/Los_Angeles")

    assert clock_service.format_utc("2026-01-15T18:00:00.000000Z") == "2026-01-15 10:00AM PST"


def test_daylight_saving_follows_the_date(account):
    settings_service.set_timezone(account.id, "America/Los_Angeles")

    assert clock_service.format_utc("2026-07-15T18:00:00.000000Z") == "2026-07-15 11:00AM PDT"


def test_the_date_can_change_across_midnight(account):
    settings_service.set_timezone(account.id, "Asia/Kolkata")

    assert clock_service.format_utc("2026-01-15T22:00:00.000000Z") == "2026-01-16 3:30AM IST"


def test_a_zone_without_a_letter_abbreviation_shows_its_offset(account):
    settings_service.set_timezone(account.id, "Europe/Istanbul")

    assert clock_service.format_utc("2026-01-15T10:00:00.000000Z") == "2026-01-15 1:00PM +03"


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


# ------------------------------------------------ specs/023 amendment: a short offset picker


def _by_value(choices):
    return {c["value"]: c["label"] for c in choices}


def test_the_picker_is_a_short_list_ordered_by_offset():
    choices = clock_service.timezone_choices("UTC")

    assert 25 <= len(choices) <= 45
    offsets = [clock_service.standard_offset_minutes(c["value"]) for c in choices]
    assert offsets == sorted(offsets)


def test_labels_read_offset_city_and_abbreviation():
    labels = _by_value(clock_service.timezone_choices("UTC"))

    assert labels["America/New_York"] == "(GMT-5) America/New York (EST)"
    assert labels["America/Los_Angeles"] == "(GMT-8) America/Los Angeles (PST)"
    assert labels["America/Chicago"] == "(GMT-6) America/Chicago (CST)"
    assert labels["Asia/Kolkata"] == "(GMT+5:30) Asia/Kolkata (IST)"
    assert labels["UTC"] == "(GMT+0) UTC"
    assert labels["Europe/London"] == "(GMT+0) Europe/London (GMT)"
    assert labels["Australia/Sydney"] == "(GMT+10) Australia/Sydney (AEST)"  # standard time, not summer
    for label in labels.values():
        assert re.fullmatch(r"\(GMT[+-]\d{1,2}(:\d\d)?\) [A-Za-z_/ ]+( \([A-Za-z, ]+\))?", label), label
        assert "_" not in label


def test_a_region_without_a_well_known_abbreviation_has_no_brackets():
    labels = _by_value(clock_service.timezone_choices("UTC"))

    assert labels["America/Sao_Paulo"] == "(GMT-3) America/Sao Paulo"
    assert labels["Asia/Kathmandu"] == "(GMT+5:45) Asia/Kathmandu"


def test_the_offset_is_the_standard_one_even_where_summer_time_is_in_force_now():
    labels = _by_value(clock_service.timezone_choices("UTC"))

    assert labels["Pacific/Auckland"] == "(GMT+12) Pacific/Auckland (NZST)"
    assert labels["Europe/Paris"] == "(GMT+1) Europe/Paris (CET)"


def test_arizona_is_offered_without_daylight_saving_beside_denver():
    labels = _by_value(clock_service.timezone_choices("UTC"))

    assert labels["America/Denver"] == "(GMT-7) America/Denver (MST)"
    assert labels["America/Phoenix"] == "(GMT-7) America/Phoenix (MST, no daylight saving)"


def test_every_choice_is_a_distinct_real_zone():
    from zoneinfo import ZoneInfo

    values = [c["value"] for c in clock_service.timezone_choices("UTC")]

    assert len(values) == len(set(values))
    for value in values:
        ZoneInfo(value)


def test_a_saved_zone_that_is_not_in_the_list_stays_selectable_and_is_marked_current():
    choices = clock_service.timezone_choices("Europe/Istanbul")

    (extra,) = [c for c in choices if c["value"] == "Europe/Istanbul"]
    assert extra["label"] == "Current: (GMT+3) Europe/Istanbul"
    assert choices[0] == extra  # listed first so it is easy to see


def test_a_saved_zone_in_the_list_adds_nothing():
    assert len(clock_service.timezone_choices("America/New_York")) == len(clock_service.timezone_choices("UTC"))


def test_times_read_on_a_twelve_hour_clock_by_default(account):
    # 036: default is 12-hour, written like 2:26PM.
    assert clock_service.clock_format() == "12"
    assert clock_service.format_utc("2026-11-13T14:26:00.000000Z") == "2026-11-13 2:26PM UTC"
    assert clock_service.format_utc("2026-11-13T12:00:00.000000Z") == "2026-11-13 12:00PM UTC"
    assert clock_service.format_utc("2026-11-13T00:05:00.000000Z") == "2026-11-13 12:05AM UTC"
    assert clock_service.format_utc("2026-11-13T07:30:00.000000Z") == "2026-11-13 7:30AM UTC"


def test_the_twenty_four_hour_clock_keeps_the_old_form(account):
    settings_service.set_clock_format(account.id, "24")

    assert clock_service.format_utc("2026-11-13T14:26:00.000000Z") == "2026-11-13 14:26 UTC"
    assert clock_service.format_wall("2026-09-02T07:30:00.000000Z") == "2026-09-02 07:30"


def test_typed_times_follow_the_clock_without_a_zone(account):
    assert clock_service.format_wall("2026-09-02T07:30:00.000000Z") == "2026-09-02 7:30AM"
    assert clock_service.format_wall("2026-09-02 19:05") == "2026-09-02 7:05PM"
    assert clock_service.format_wall("") == "" and clock_service.format_wall(None) == ""
    assert clock_service.format_wall("not a time") == "not a time"


def test_a_system_recorded_instant_is_shown_in_the_zone_but_a_typed_time_is_shown_as_typed(account):
    # 023 FR-008 (049): 4:03 AM UTC recorded by the app is 11:03 PM the evening before in New York.
    settings_service.set_timezone(account.id, "America/New_York")
    settings_service.set_clock_format(account.id, "24")

    assert clock_service.format_wall("2026-11-14T04:03:21.123456Z") == "2026-11-13 23:03"
    assert clock_service.format_wall("2026-11-14T04:03:00.000000Z") == "2026-11-14 04:03"  # typed: as typed
    assert clock_service.to_wall("2026-11-14T04:03:21.123456Z") == "2026-11-13T23:03"
    assert clock_service.to_wall("2026-11-14T04:03:00.000000Z") == "2026-11-14T04:03"
    assert clock_service.to_wall(None) == "" and clock_service.to_wall("junk") == "junk"


def test_summer_time_is_applied_to_recorded_instants(account):
    settings_service.set_timezone(account.id, "America/New_York")

    assert clock_service.format_wall("2026-07-01T03:30:10.500000Z") == "2026-06-30 11:30PM"

