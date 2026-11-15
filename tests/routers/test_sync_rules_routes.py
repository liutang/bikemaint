"""Sync rules on the bike and part Edit screens (specs/060-sync-rules)."""

import re

import pytest

from app.db import connection, mileage
from app.services import bike_service, component_service, sync_rule_service


@pytest.mark.parametrize("path", ["/bikes/1/sync-rules", "/components/1/sync-rules"])
def test_saving_requires_sign_in(client, path):
    response = client.post(path, follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == "/login"


def test_unknown_items_are_404(signed_in_client):
    assert signed_in_client.post("/bikes/99/sync-rules", data={}).status_code == 404
    assert signed_in_client.post("/components/99/sync-rules", data={}).status_code == 404


@pytest.mark.parametrize("kind", ["bike", "component"])
def test_the_edit_screen_offers_sport_ride_type_and_keywords(signed_in_client, kind):
    bike = bike_service.create_bike(name="Road")
    part = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    owner = bike if kind == "bike" else part
    sync_rule_service.save_rule(kind, owner.id, sports=["GravelRide"], ride_types=["race"], keywords="commute")

    html = signed_in_client.get(f"/{kind}s/{owner.id}/edit").text

    assert "Sync rules" in html and f'action="/{kind}s/{owner.id}/sync-rules"' in html
    assert re.search(r'<input[^>]*name="sport"[^>]*value="GravelRide"[^>]*checked', html)
    assert re.search(r'<input[^>]*name="sport"[^>]*value="Ride"(?![^>]*checked)', html)
    assert re.search(r'<input[^>]*name="ride_type"[^>]*value="race"[^>]*checked', html)
    assert re.search(r'<input[^>]*name="keywords"[^>]*value="commute"', html)
    assert ">Save rules</button>" in html


def test_new_item_forms_have_the_rules_inside_the_form_not_a_separate_one(signed_in_client):
    # specs/062 replaced "no rules on new forms": the fields are part of the create form.
    for path in ("/bikes/new", "/components/new"):
        html = signed_in_client.get(path).text
        assert "Sync rules" in html and "sync-rules" not in html.split("<main")[1]


def test_saving_a_bike_rule_filters_its_rides_and_returns_to_edit(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    with connection.get_connection() as conn:
        for n, miles, rtype in ((1, 10, "default"), (2, 20, "race")):
            mileage.upsert_ride_activity(
                conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles,
                occurred_at=f"2024-06-0{n}T12:00:00.000000Z", sport_type="Ride", ride_type=rtype, activity_name="x",
            )
        mileage.recompute_bike_total_mileage(conn, bike.id)

    response = signed_in_client.post(
        f"/bikes/{bike.id}/sync-rules", data={"sport": ["Ride"], "ride_type": ["race"], "keywords": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/edit"
    assert bike_service.get_bike(bike.id).total_mileage == 20
    assert sync_rule_service.get_rule("bike", bike.id).ride_types == "race"


def test_saving_a_part_rule_redirects_to_the_part_edit_screen(signed_in_client):
    part = component_service.create_component(name="Chain", component_type="chain")

    response = signed_in_client.post(
        f"/components/{part.id}/sync-rules", data={"keywords": " Commute , zwift"}, follow_redirects=False
    )

    assert response.status_code == 303 and response.headers["location"] == f"/components/{part.id}/edit"
    assert sync_rule_service.get_rule("component", part.id).keywords == "commute,zwift"


def test_too_many_keywords_are_refused_beside_the_field(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    response = signed_in_client.post(f"/bikes/{bike.id}/sync-rules", data={"keywords": ",".join(f"k{i}" for i in range(11))})

    assert response.status_code == 422 and "at most 10 keywords" in response.text and "Sync rules" in response.text
