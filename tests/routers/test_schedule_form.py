"""The schedule form: service type, one interval, recurring and notify (specs/040)."""

import re

import pytest

from app.services import bike_service, schedule_service

SERVICES = ["Charge", "Check", "Clean", "Lube/Wax", "Replace", "Service", "Topup"]


def _data(**kw):
    return {"service_type": "Replace", "interval_kind": "usage", "interval_unit_usage": "miles",
            "interval_unit_period": "weeks", "interval_value": "2000", "is_recurring": "on", "notify": "on", **kw}


def _bike():
    return bike_service.create_bike(name="Road Bike")


def _options(html, name):
    select = re.search(rf'<select[^>]*name="{name}"[^>]*>(.*?)</select>', html, re.S).group(1)
    return re.findall(r'<option value="([^"]*)"', select)


def test_the_new_form_offers_exactly_the_service_types_and_the_units_of_each_kind(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}/schedules/new").text

    assert [o for o in _options(html, "service_type") if o] == SERVICES
    assert _options(html, "interval_unit_usage") == ["miles", "rides", "hours"]
    assert _options(html, "interval_unit_period") == ["years", "months", "weeks"]
    assert 'name="name"' not in html and 'name="interval_miles"' not in html


def test_the_new_form_starts_with_usage_recurring_and_notifications_on(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}/schedules/new").text

    assert re.search(r'<input[^>]*id="interval-usage"[^>]*checked', html)
    assert not re.search(r'<input[^>]*id="interval-period"[^>]*checked', html)
    assert re.search(r'<input[^>]*name="is_recurring"[^>]*checked', html)
    assert re.search(r'<input[^>]*name="notify"[^>]*checked', html)
    assert "Recurring" in html and "Receive notifications" in html


@pytest.mark.parametrize("kind,unit_field,unit,expect_unit", [
    ("usage", "interval_unit_usage", "rides", "rides"),
    ("usage", "interval_unit_usage", "hours", "hours"),
    ("period", "interval_unit_period", "months", "months"),
    ("period", "interval_unit_period", "years", "years"),
])
def test_creating_a_schedule_stores_the_kind_and_the_matching_unit(signed_in_client, kind, unit_field, unit, expect_unit):
    bike = _bike()
    data = _data(interval_kind=kind, interval_value="3", **{unit_field: unit})

    response = signed_in_client.post(f"/bikes/{bike.id}/schedules", data=data, follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}/schedules")
    (schedule,) = schedule_service.list_for_bike(bike.id)
    assert (schedule.service_type, schedule.interval_kind, schedule.interval_unit, schedule.interval_value) == (
        "Replace", kind, expect_unit, 3.0)
    assert (schedule.is_recurring, schedule.notify) == (True, True)


def test_unchecked_switches_are_saved_as_off(signed_in_client):
    bike = _bike()
    data = _data()
    del data["is_recurring"], data["notify"]

    signed_in_client.post(f"/bikes/{bike.id}/schedules", data=data)

    (schedule,) = schedule_service.list_for_bike(bike.id)
    assert (schedule.is_recurring, schedule.notify) == (False, False)


@pytest.mark.parametrize("bad,field", [
    ({"service_type": ""}, "service_type"), ({"service_type": "Polish"}, "service_type"),
    ({"interval_value": ""}, "interval_value"), ({"interval_value": "0"}, "interval_value"),
    ({"interval_unit_usage": "years"}, "interval_unit_usage"),
    ({"interval_kind": "period", "interval_unit_period": "miles"}, "interval_unit_period"),
    ({"interval_unit_usage": "rides", "interval_value": "2.5"}, "interval_value"),
])
def test_bad_input_is_refused_beside_the_field_and_nothing_is_saved(signed_in_client, bad, field):
    bike = _bike()

    response = signed_in_client.post(f"/bikes/{bike.id}/schedules", data=_data(**bad))

    assert response.status_code == 422
    assert f'id="{field}-error"' in response.text
    assert schedule_service.list_for_bike(bike.id) == []


def test_a_refused_form_keeps_what_was_chosen_including_switches(signed_in_client):
    bike = _bike()
    data = _data(interval_kind="period", interval_unit_period="months", interval_value="0")
    del data["notify"]

    html = signed_in_client.post(f"/bikes/{bike.id}/schedules", data=data).text

    assert re.search(r'<input[^>]*id="interval-period"[^>]*checked', html)
    assert '<option value="months" selected>' in html
    assert re.search(r'<input[^>]*name="is_recurring"[^>]*checked', html)
    assert not re.search(r'<input[^>]*name="notify"[^>]*checked', html)


def test_a_typed_schedule_opens_for_edit_with_its_values(signed_in_client):
    bike = _bike()
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Clean", interval_kind="period", interval_value=2, interval_unit="months",
        is_recurring=False, notify=False,
    )

    html = signed_in_client.get(f"/schedules/{schedule.id}/edit").text

    assert '<option value="Clean" selected>' in html and '<option value="months" selected>' in html
    assert re.search(r'<input[^>]*id="interval-period"[^>]*checked', html)
    assert not re.search(r'<input[^>]*name="is_recurring"[^>]*checked', html)
    assert not re.search(r'<input[^>]*name="notify"[^>]*checked', html)
    assert "created before" not in html


def test_an_old_schedule_opens_with_an_empty_service_type_and_a_prefilled_interval(signed_in_client):
    bike = _bike()
    miles = schedule_service.create_schedule(bike_id=bike.id, name="lube chain", interval_miles=250)
    days = schedule_service.create_schedule(bike_id=bike.id, name="annual", interval_days=365)
    both = schedule_service.create_schedule(bike_id=bike.id, name="both", interval_miles=100, interval_days=30)

    m = signed_in_client.get(f"/schedules/{miles.id}/edit").text
    d = signed_in_client.get(f"/schedules/{days.id}/edit").text
    b = signed_in_client.get(f"/schedules/{both.id}/edit").text

    assert "created before" in m and not re.search(r'<option value="[A-Z][^"]*" selected>', m.split('name="service_type"')[1].split("</select>")[0])
    assert re.search(r'<input[^>]*id="interval-usage"[^>]*checked', m) and '<option value="miles" selected>' in m
    assert re.search(r'name="interval_value"[^>]*value="250"', m) or re.search(r'value="250"[^>]*name="interval_value"', m)
    assert re.search(r'<input[^>]*id="interval-period"[^>]*checked', d) and '<option value="weeks" selected>' in d
    assert re.search(r'value="52"[^>]*', d)  # 365 days is about 52 weeks
    assert re.search(r'<input[^>]*id="interval-usage"[^>]*checked', b)  # the mileage side is prefilled


def test_saving_an_old_schedule_converts_it(signed_in_client):
    bike = _bike()
    old = schedule_service.create_schedule(bike_id=bike.id, name="lube chain", interval_miles=250)

    response = signed_in_client.post(f"/schedules/{old.id}", data=_data(service_type="Lube/Wax", interval_value="250", is_active="on"),
                                     follow_redirects=False)

    assert response.status_code == 303
    new = schedule_service.get_schedule(old.id)
    assert (new.name, new.service_type, new.interval_unit, new.cycle_number) == ("Lube/Wax", "Lube/Wax", "miles", 1)


def test_the_units_are_shown_by_css_only_with_no_script(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}/schedules/new").text
    css = open("app/static/styles.css").read()

    assert "<script" not in html.split("<main")[1]
    assert ":has(#interval-usage:checked)" in css and ":has(#interval-period:checked)" in css


def test_the_board_names_the_unit_left(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="usage", interval_value=10, interval_unit="hours")

    html = signed_in_client.get("/maintenance/due?all=1").text

    assert "Check" in html and "10.0 hours left" in html


def test_adding_a_topup_schedule_to_a_part_with_an_old_topup_shows_overdue(signed_in_client):
    # 040 FR-011, the rider's case: Topup logged 2023-09-01, then Topup every 4 months.
    from app.services import component_service, maintenance_service

    wheel = component_service.create_component(name="Front wheel", component_type="wheel")
    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2023-09-01")

    signed_in_client.post(
        f"/components/{wheel.id}/schedules",
        data=_data(service_type="Topup", interval_kind="period", interval_unit_period="months", interval_value="4"),
    )

    html = signed_in_client.get("/maintenance/due?all=1").text
    row = re.search(r'<(?:article|li) class="(?:attention-card|other-row)[^"]*" id="schedule-row-1">.*?</(?:article|li)>', html, re.S).group(0)
    assert "Overdue" in row or "overdue" in row
    assert "2024-01-01" in row
