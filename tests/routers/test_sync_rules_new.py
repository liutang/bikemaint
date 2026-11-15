"""Sync rules on the Add bike and Add part forms (specs/062-sync-rules-on-new)."""

import pytest

from app.services import bike_service, component_service, sync_rule_service

BIKE = {"year": "2022", "make": "Trek", "model": "Domane", "category": "road", "manual_baseline_mileage": "0"}
PART = {"name": "Chain", "component_type": "chain", "manual_baseline_mileage": "0"}


@pytest.mark.parametrize("path", ["/bikes/new", "/components/new"])
def test_the_add_forms_offer_the_rules_inside_the_form(signed_in_client, path):
    html = signed_in_client.get(path).text

    assert 'name="sport"' in html and 'name="ride_type"' in html and 'name="keywords"' in html
    assert "Save rules" not in html


@pytest.mark.parametrize("path,base,kind", [("/bikes", BIKE, "bike"), ("/components", PART, "component")])
def test_rules_filled_in_are_saved_with_the_new_item(signed_in_client, path, base, kind):
    data = {**base, "sport": ["GravelRide"], "ride_type": ["race"], "keywords": "Commute, work"}

    response = signed_in_client.post(path, data=data, follow_redirects=False)

    assert response.status_code == 303
    new_id = int(response.headers["location"].rsplit("/", 1)[1])
    rule = sync_rule_service.get_rule(kind, new_id)
    assert (rule.sports, rule.ride_types, rule.keywords) == ("GravelRide", "race", "commute,work")


@pytest.mark.parametrize("path,base,kind", [("/bikes", BIKE, "bike"), ("/components", PART, "component")])
def test_no_rules_means_no_rule(signed_in_client, path, base, kind):
    response = signed_in_client.post(path, data=base, follow_redirects=False)

    new_id = int(response.headers["location"].rsplit("/", 1)[1])
    rule = sync_rule_service.get_rule(kind, new_id)
    assert (rule.sports, rule.ride_types, rule.keywords) == ("", "", "")


@pytest.mark.parametrize("path,base", [("/bikes", BIKE), ("/components", PART)])
def test_bad_rules_refuse_the_form_create_nothing_and_keep_the_input(signed_in_client, path, base):
    data = {**base, "sport": ["Skateboard"], "keywords": "x" * 500, "ride_type": ["race"]}

    response = signed_in_client.post(path, data=data)

    assert response.status_code == 422
    assert 'id="sync-rules-error"' in response.text
    assert bike_service.list_bikes() == [] and component_service.list_in_storage() == []
    assert 'value="race" checked' in response.text
