"""The schedule form's boundary validation (specs/040-schedule-types-and-intervals)."""

import pytest
from pydantic import ValidationError

from app.models.requests import ScheduleRequest


def _ok(**kw):
    data = dict(service_type="Replace", interval_kind="usage", interval_value="2000",
                interval_unit_usage="miles", interval_unit_period="", is_recurring=True, notify=True)
    return {**data, **kw}


def test_a_valid_usage_schedule_picks_the_usage_unit():
    request = ScheduleRequest(**_ok())

    assert (request.service_type, request.interval_kind, request.interval_value, request.interval_unit) == (
        "Replace", "usage", 2000.0, "miles")


def test_a_valid_period_schedule_picks_the_period_unit():
    request = ScheduleRequest(**_ok(interval_kind="period", interval_value="3", interval_unit_period="months"))

    assert (request.interval_kind, request.interval_unit, request.interval_value) == ("period", "months", 3.0)


@pytest.mark.parametrize("service", ["Charge", "Check", "Clean", "Lube/Wax", "Replace", "Service", "Topup"])
def test_every_listed_service_type_is_accepted(service):
    assert ScheduleRequest(**_ok(service_type=service)).service_type == service


@pytest.mark.parametrize("bad", [
    {"service_type": ""}, {"service_type": "Polish"}, {"service_type": "replace"},
    {"interval_kind": "both"}, {"interval_kind": ""},
    {"interval_value": ""}, {"interval_value": "0"}, {"interval_value": "-4"}, {"interval_value": "abc"},
    {"interval_unit_usage": "months"},                       # period unit for a usage schedule
    {"interval_kind": "period", "interval_unit_period": "miles"},
    {"interval_kind": "period", "interval_unit_period": ""},
    {"interval_unit_usage": "rides", "interval_value": "2.5"},
    {"interval_kind": "period", "interval_unit_period": "weeks", "interval_value": "1.5"},
])
def test_invalid_input_is_refused(bad):
    with pytest.raises(ValidationError):
        ScheduleRequest(**_ok(**bad))


def test_flags_default_to_on():
    request = ScheduleRequest(service_type="Check", interval_kind="usage", interval_value="5",
                              interval_unit_usage="hours")

    assert (request.is_recurring, request.notify, request.is_active) == (True, True, True)
