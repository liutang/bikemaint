"""Placement rules through the existing forms and routes (specs/004-bike-builder, M2)."""

import re

import pytest

from app.services import bike_service, component_service


def _bike(name="Road Bike"):
    return bike_service.create_bike(name=name)


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def _options(html, select_id):
    block = re.search(rf'<select id="{select_id}".*?</select>', html, re.S).group(0)
    return re.findall(r'<option value="([^"]*)"', block)


# --- create form


def test_creating_a_pedal_on_a_wheel_is_refused_with_a_clear_message(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = signed_in_client.post(
        "/components",
        data={"name": "Pedal", "component_type": "pedal", "parent_component_id": str(wheel.id)},
    )

    assert response.status_code == 422
    assert "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert component_service.get_descendants(wheel.id) == []


def test_creating_a_tire_on_a_rim_works(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)

    response = signed_in_client.post(
        "/components",
        data={"name": "Tire", "component_type": "tire", "parent_component_id": str(rim.id)},
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_add_form_for_storage_offers_every_type(signed_in_client):
    types = _options(signed_in_client.get("/components/new").text, "component_type")

    assert types == ["frame", "fork", "wheel", "tire", "rotor", "brake", "drivetrain", "chain", "pedal", "saddle", "handlebar", "other"]


def test_failed_create_keeps_the_filtered_type_list(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = signed_in_client.post(
        "/components",
        data={"name": "Pedal", "component_type": "pedal", "parent_component_id": str(wheel.id)},
    )

    assert "pedal" not in _options(response.text, "component_type")


# --- edit form


def test_changing_a_type_to_one_that_does_not_fit_is_refused(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    hub = _mk("Hub", "hub", parent_component_id=wheel.id)

    response = signed_in_client.post(
        f"/components/{hub.id}",
        data={"name": "Hub", "component_type": "saddle", "manual_baseline_mileage": "0"},
    )

    assert response.status_code == 422
    assert "A saddle can be mounted on the bike, not on a wheel." in response.text


# --- move control (the no-JS "Move to..." alternative)


def test_moving_with_the_target_field_works(signed_in_client):
    bike = _bike()
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = signed_in_client.post(
        f"/components/{pedal.id}/move", data={"target": f"component:{crank.id}"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert component_service.get_component(pedal.id).parent_component_id == crank.id


def test_moving_to_storage_with_the_target_field_works(signed_in_client):
    bike = _bike()
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal", parent_component_id=crank.id)

    signed_in_client.post(f"/components/{pedal.id}/move", data={"target": "storage"})

    assert component_service.get_component(pedal.id).parent_component_id is None


def test_moving_to_an_invalid_target_is_refused_with_the_rule_message(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = signed_in_client.post(
        f"/components/{pedal.id}/move", data={"target": f"component:{wheel.id}"}
    )

    assert response.status_code == 422
    assert "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert component_service.get_component(pedal.id).parent_component_id is None


def test_the_legacy_parent_id_fields_are_validated_by_the_same_rules(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = signed_in_client.post(
        f"/components/{pedal.id}/move", data={"parent_component_id": str(wheel.id)}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("bad", ["bike:abc", "component:", "x", "storage;drop", "bike:1:2", "bike:-1"])
def test_malformed_targets_are_rejected_and_nothing_moves(signed_in_client, bad):
    bike = _bike()
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal", parent_component_id=crank.id)

    response = signed_in_client.post(f"/components/{pedal.id}/move", data={"target": bad})

    assert response.status_code == 422
    assert component_service.get_component(pedal.id).parent_component_id == crank.id


def test_a_target_pointing_at_a_missing_component_is_refused(signed_in_client):
    pedal = _mk("Pedal", "pedal")

    response = signed_in_client.post(f"/components/{pedal.id}/move", data={"target": "component:999"})

    assert response.status_code == 422
    assert component_service.get_component(pedal.id).parent_component_id is None


# --- simplified part categories (specs/005-unified-bike-screen, M1)


def test_creating_a_part_of_an_older_finer_kind_is_rejected(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = signed_in_client.post(
        "/components", data={"name": "Rim", "component_type": "rim", "parent_component_id": str(wheel.id)}
    )

    assert response.status_code == 422
    assert component_service.get_descendants(wheel.id) == []


def test_an_existing_older_kind_part_can_be_edited_without_changing_its_type(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)  # as created before the simplification

    html = signed_in_client.get(f"/components/{rim.id}/edit").text
    assert '<option value="rim" selected>' in html  # its own kind stays selectable
    response = signed_in_client.post(
        f"/components/{rim.id}",
        data={"name": "Rim renamed", "component_type": "rim", "manual_baseline_mileage": "5"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert component_service.get_component(rim.id).name == "Rim renamed"


def test_an_older_kind_part_still_appears_moves_and_returns_to_storage(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    spoke = _mk("Spoke", "spoke", parent_component_id=wheel.id)

    assert "Spoke" in signed_in_client.get(f"/bikes/{bike.id}").text
    signed_in_client.post(f"/components/{spoke.id}/move", data={"target": "storage"})

    assert component_service.get_component(spoke.id).parent_component_id is None


# --- the Add part form (specs/006, M1)


def test_the_add_part_form_shows_no_parent_ids(signed_in_client):
    html = signed_in_client.get("/components/new").text

    assert 'name="parent_bike_id"' not in html and 'name="parent_component_id"' not in html
    assert "Parent bike ID" not in html and "Parent component ID" not in html
    assert 'name="name"' in html and 'name="component_type"' in html and 'name="manual_baseline_mileage"' in html


def test_the_add_part_form_ignores_parent_query_parameters(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/components/new?parent_bike_id={bike.id}").text

    assert 'name="parent_bike_id"' not in html


def test_adding_a_part_with_the_form_puts_it_in_storage(signed_in_client):
    response = signed_in_client.post(
        "/components", data={"name": "Spare saddle", "component_type": "saddle", "manual_baseline_mileage": "0"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert [c.name for c in component_service.list_in_storage()] == ["Spare saddle"]


def test_the_add_part_form_offers_every_kind_and_cancels_back_to_storage(signed_in_client):
    html = signed_in_client.get("/components/new").text

    assert len(_options(html, "component_type")) == 12
    assert 'href="/components">Cancel</a>' in html
