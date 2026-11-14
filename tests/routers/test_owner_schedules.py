"""The Schedules page of a bike or part (specs/056-schedules-page)."""

import re

import pytest

from app.services import bike_service, component_service, schedule_service

TYPED = {"service_type": "Lube/Wax", "interval_kind": "usage", "interval_unit": "miles", "interval_value": 186}
FORM = {"service_type": "Clean", "interval_kind": "period", "interval_unit_period": "months",
        "interval_value": "4", "is_recurring": "on", "notify": "on"}


@pytest.mark.parametrize("path", ["/bikes/1/schedules", "/components/1/schedules"])
def test_the_pages_require_sign_in(client, path):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == "/login"


def test_unknown_items_are_404(signed_in_client):
    assert signed_in_client.get("/bikes/99/schedules").status_code == 404
    assert signed_in_client.get("/components/99/schedules").status_code == 404


def test_the_bike_and_part_screens_have_a_schedules_button_not_add_schedule(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)

    for base, owner_id in (("/bikes", bike.id), ("/components", chain.id)):
        html = signed_in_client.get(f"{base}/{owner_id}").text
        assert f'class="btn" href="{base}/{owner_id}/schedules">Schedules</a>' in html
        assert "Add schedule" not in html


def test_the_page_lists_only_this_items_schedules_with_actions(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    mine = schedule_service.create_schedule(component_id=chain.id, **TYPED)
    schedule_service.create_schedule(
        component_id=chain.id, service_type="Clean", interval_kind="period", interval_unit="months",
        interval_value=4, is_recurring=False, notify=False,
    )
    schedule_service.create_schedule(bike_id=bike.id, **{**TYPED, "service_type": "Check"})

    html = signed_in_client.get(f"/components/{chain.id}/schedules").text

    body = html.split("<tbody>")[1]
    rows = re.findall(r"<tr[^>]*>.*?</tr>", body, re.S)
    assert len(rows) == 2 and "Check" not in body
    assert "Every 186 miles" in rows[0] and "Recurring" in rows[0] and "On" in rows[0]
    assert "Every 4 months" in rows[1] and "One-time" in rows[1] and "Off" in rows[1]
    assert f'class="btn" href="/schedules/{mine.id}/edit?from=owner"' in rows[0]
    assert f'action="/schedules/{mine.id}/delete?from=owner"' in rows[0] and ">Delete</button>" in rows[0]
    assert f'href="/components/{chain.id}/schedules/new"' in html and "btn-quiet" not in html


def test_an_item_without_schedules_shows_an_empty_state(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/schedules").text

    assert "No schedules yet" in html and f'href="/bikes/{bike.id}/schedules/new"' in html


def test_adding_returns_to_the_schedules_page_and_cancel_goes_there_too(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    form = signed_in_client.get(f"/bikes/{bike.id}/schedules/new").text
    response = signed_in_client.post(f"/bikes/{bike.id}/schedules", data=FORM, follow_redirects=False)

    assert f'href="/bikes/{bike.id}/schedules"' in form
    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/schedules"


def test_edit_from_the_page_returns_to_the_page_but_from_due_returns_to_due(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(bike_id=bike.id, **TYPED)

    owner_form = signed_in_client.get(f"/schedules/{schedule.id}/edit?from=owner").text
    due_form = signed_in_client.get(f"/schedules/{schedule.id}/edit").text
    saved = signed_in_client.post(f"/schedules/{schedule.id}?from=owner", data={**FORM, "is_active": "on"}, follow_redirects=False)
    saved_due = signed_in_client.post(f"/schedules/{schedule.id}", data={**FORM, "is_active": "on"}, follow_redirects=False)

    assert f'action="/schedules/{schedule.id}?from=owner"' in owner_form
    assert f'href="/bikes/{bike.id}/schedules"' in owner_form
    assert 'href="/maintenance/due"' in due_form and "from=owner" not in due_form
    assert saved.headers["location"] == f"/bikes/{bike.id}/schedules"
    assert saved_due.headers["location"] == "/maintenance/due"


def test_a_refused_edit_keeps_the_owner_flag(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(bike_id=bike.id, **TYPED)

    response = signed_in_client.post(f"/schedules/{schedule.id}?from=owner", data={"service_type": ""})

    assert response.status_code == 422 and f'action="/schedules/{schedule.id}?from=owner"' in response.text


def test_delete_from_the_page_returns_to_the_page_and_removes_the_row(signed_in_client):
    chain = component_service.create_component(name="Chain", component_type="chain")
    schedule = schedule_service.create_schedule(component_id=chain.id, **TYPED)

    response = signed_in_client.post(f"/schedules/{schedule.id}/delete?from=owner", follow_redirects=False)
    elsewhere = signed_in_client.post(f"/schedules/{schedule.id}/delete?from=//evil.example", follow_redirects=False)

    assert response.headers["location"] == f"/components/{chain.id}/schedules"
    assert "No schedules yet" in signed_in_client.get(f"/components/{chain.id}/schedules").text
    assert elsewhere.headers["location"] == "/maintenance/due"  # only the fixed flag is honored
