"""Validation of the sync and time zone settings (specs/023-settings-sync-and-timezone)."""

import pytest
from pydantic import ValidationError

from app.models.requests import SyncSettingsRequest, TimezoneSettingsRequest


def _sync(hours, minutes, enabled=True):
    return SyncSettingsRequest(sync_enabled=enabled, interval_hours=hours, interval_minutes=minutes)


@pytest.mark.parametrize("hours,minutes,total", [(0, 5, 5), (0, 30, 30), (1, 30, 90), (2, 15, 135), (168, 0, 10080)])
def test_valid_intervals_become_total_minutes(hours, minutes, total):
    assert _sync(hours, minutes).total_minutes == total


@pytest.mark.parametrize("hours,minutes", [(0, 0), (0, 4), (168, 1), (169, 0), (0, 60), (-1, 30), (1, -5)])
def test_intervals_outside_five_minutes_to_seven_days_are_refused(hours, minutes):
    with pytest.raises(ValidationError):
        _sync(hours, minutes)


@pytest.mark.parametrize("hours,minutes", [("x", "30"), ("1", "2.5"), ("", "30"), ("1", "")])
def test_non_integers_and_blanks_are_refused(hours, minutes):
    with pytest.raises(ValidationError):
        _sync(hours, minutes)


def test_numbers_typed_into_the_form_are_accepted_as_text():
    assert _sync("1", "30").total_minutes == 90


@pytest.mark.parametrize("name", ["UTC", "America/Los_Angeles", "Europe/London", "Asia/Kolkata"])
def test_known_zone_names_are_accepted(name):
    assert TimezoneSettingsRequest(timezone=name).timezone == name


@pytest.mark.parametrize("name", ["", "   ", "Mars/Olympus", "../etc/passwd", "america/los_angeles ", "PST8PDTX"])
def test_unknown_or_malformed_zone_names_are_refused(name):
    with pytest.raises(ValidationError):
        TimezoneSettingsRequest(timezone=name)
