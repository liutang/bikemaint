"""Bike and part Edit save details and sync rules with one Save (specs/071-ui-consistency US3)."""

import re

import pytest

from app.services import bike_service, component_service, sync_rule_service


def _bike():
    return bike_service.create_bike_from_details(year=2014, make="Trek", model="Madone 2.1", category="road", manual_baseline_mileage=0)


BIKE = {"sync_rules": "1", "year": "2014", "make": "Trek", "model": "Madone 2.1", "category": "road", "manual_baseline_mileage": "0"}


@pytest.mark.parametrize("kind", ["bike", "component"])
def test_the_edit_screen_has_one_form_and_one_save(signed_in_client, kind):
    bike = _bike()
    owner = bike if kind == "bike" else component_service.create_component(name="Chain", component_type="chain")

    html = signed_in_client.get(f"/{kind}s/{owner.id}/edit").text
    main = html.split("<main")[1]

    assert "Save rules" not in main and "/sync-rules" not in main
    assert len(re.findall(r">\s*Save\s*</button>", main)) == 1
    form = re.search(rf'<form[^>]*action="/{kind}s/{owner.id}"[^>]*>(.*?)</form>', main, re.S).group(1)
    assert 'name="sport"' in form and 'name="keywords"' in form and 'class="card-grid"' in form


def test_saving_the_bike_saves_its_rule_and_an_empty_rule_removes_it(signed_in_client):
    bike = _bike()

    r = signed_in_client.post(f"/bikes/{bike.id}", data={**BIKE, "sport": ["Ride"], "keywords": "commute"}, follow_redirects=False)
    assert r.status_code == 303
    rule = sync_rule_service.get_rule("bike", bike.id)
    assert (rule.sports, rule.keywords) == ("Ride", "commute")

    signed_in_client.post(f"/bikes/{bike.id}", data=BIKE)
    assert sync_rule_service.get_rule("bike", bike.id).keywords == ""


def test_saving_the_part_saves_its_rule(signed_in_client):
    part = component_service.create_component(name="Chain", component_type="chain")

    signed_in_client.post(f"/components/{part.id}", data={"sync_rules": "1", "name": "Chain", "component_type": "chain",
                                                         "manual_baseline_mileage": "0", "ride_type": ["race"]})

    assert sync_rule_service.get_rule("component", part.id).ride_types == "race"


def test_a_bad_rule_refuses_the_whole_save_and_keeps_the_input(signed_in_client):
    bike = _bike()

    r = signed_in_client.post(f"/bikes/{bike.id}", data={**BIKE, "model": "Domane", "sport": ["Skateboard"], "ride_type": ["race"]})

    assert r.status_code == 422 and 'id="sync-rules-error"' in r.text
    assert bike_service.get_bike(bike.id).model == "Madone 2.1"
    assert 'value="race" checked' in r.text and 'value="Domane"' in r.text


def test_the_part_screens_say_part_in_the_tab(signed_in_client):
    part = component_service.create_component(name="Chain", component_type="chain")

    assert "<title>Edit part" in signed_in_client.get(f"/components/{part.id}/edit").text
    assert "<title>Add part" in signed_in_client.get("/components/new").text


def test_a_post_without_the_rule_fields_leaves_the_rule_alone(signed_in_client):
    bike = _bike()
    sync_rule_service.save_rule("bike", bike.id, sports=["Ride"], ride_types=[], keywords="")
    details = {k: v for k, v in BIKE.items() if k != "sync_rules"}

    signed_in_client.post(f"/bikes/{bike.id}", data=details)

    assert sync_rule_service.get_rule("bike", bike.id).sports == "Ride"
