"""Interactive builder routes (specs/004-bike-builder, M3)."""

import re

import pytest

from app.services import bike_service, component_service


def _bike(name="Road"):
    return bike_service.create_bike(name=name)


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def _hx(client, path, data):
    return client.post(path, data=data, headers={"hx-request": "true"})


def _names(bike_id):
    return [c.name for c in component_service.get_tree_for_bike(bike_id)]


# ---------------------------------------------------------------- auth / 404


@pytest.mark.parametrize(
    "method,path",
    [("get", "/bikes/1/build"), ("post", "/bikes/1/build/add"), ("post", "/bikes/1/build/move")],
)
def test_builder_routes_require_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_builder_page_for_a_missing_bike_is_a_404(signed_in_client):
    assert signed_in_client.get("/bikes/99/build").status_code == 404
    assert signed_in_client.post("/bikes/99/build/add", data={"component_type": "frame", "target": "bike:99"}).status_code == 404


# ---------------------------------------------------------------- page markup


def test_page_has_two_panes_with_tree_left_and_list_right(signed_in_client):
    bike = _bike("Trek Domane")
    frame = _mk("Frame", "frame", parent_bike_id=bike.id)
    _mk("Spare saddle", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    assert re.search(r"<h1[^>]*>.*Trek Domane", html, re.S)
    assert '<div id="builder" class="builder"' in html
    tree_at = html.index('class="builder-tree"')
    side_at = html.index('class="builder-side"')
    assert tree_at < side_at  # tree first (left on wide screens, on top when stacked)
    assert 'src="' in html and "builder.js" in html
    assert f'data-id="{frame.id}"' in html


def test_bike_root_is_a_drop_target_with_its_accepted_types(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    root = re.search(r'<div class="builder-root drop-target"[^>]*>', html).group(0)
    assert f'data-ref="bike:{bike.id}"' in root
    accepts = re.search(r'data-accepts="([^"]*)"', root).group(1).split()
    assert "frame" in accepts and "wheel" in accepts and "tire" not in accepts
    assert "Drag a frame here to start" in html


def test_tree_nodes_are_draggable_drop_targets_with_rules_attached(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    node = re.search(rf'<div class="node-row drop-target"[^>]*data-id="{wheel.id}"[^>]*>', html).group(0)
    assert 'draggable="true"' in node and 'data-source="node"' in node and 'data-type="wheel"' in node
    assert f'data-ref="component:{wheel.id}"' in node and f'data-parent-ref="bike:{bike.id}"' in node
    accepts = re.search(r'data-accepts="([^"]*)"', node).group(1).split()
    assert "other" in accepts and "tire" not in accepts  # the single tire slot is taken


def test_storage_and_palette_items_are_draggable_sources(signed_in_client):
    bike = _bike()
    spare = _mk("Spare hub", "hub")

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    assert re.search(rf'<li class="side-item"[^>]*draggable="true"[^>]*data-source="storage"[^>]*data-id="{spare.id}"', html)
    palette = re.findall(r'data-source="palette" data-type="([a-z]+)"', html)
    assert {"frame", "pedal", "tire", "saddle"} <= set(palette)
    assert 'data-ref="storage"' in html  # drop here to unmount


def test_every_drag_action_has_a_keyboard_form_with_only_valid_targets(signed_in_client):
    bike = _bike("Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Spare tire", "tire")

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    # storage item: "Add to" select listing the wheel only
    forms = re.findall(r'<form class="side-form"[^>]*action="/bikes/%d/build/move".*?</form>' % bike.id, html, re.S)
    assert forms and f'value="component:{wheel.id}"' in forms[0] and "<select" in forms[0]
    assert 'name="component_id"' in forms[0] and 'name="target"' in forms[0]
    # palette: "Add" select for hubs lists the wheel; pedals have no valid place so no form control
    add_forms = re.findall(r'<form class="side-form"[^>]*action="/bikes/%d/build/add".*?</form>' % bike.id, html, re.S)
    assert any('name="component_type" value="tire"' in f and f'value="component:{wheel.id}"' in f for f in add_forms)
    assert not any('value="rim"' in f for f in add_forms)  # older finer kinds are never offered


def test_reorder_buttons_exist_for_siblings(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1 = _mk("S1", "spoke", parent_component_id=wheel.id)
    s2 = _mk("S2", "spoke", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    assert re.search(rf'aria-label="Move S2 up"', html) and 'aria-label="Move S1 down"' in html
    assert 'aria-label="Move S1 up"' not in html and 'aria-label="Move S2 down"' not in html
    up = re.search(r'<form class="node-form"[^>]*>(?:(?!</form>).)*aria-label="Move S2 up".*?</form>', html, re.S).group(0)
    assert f'name="before_component_id" value="{s1.id}"' in up and f'name="component_id" value="{s2.id}"' in up


def test_page_works_without_scripts_forms_have_plain_post_actions(signed_in_client):
    bike = _bike()
    _mk("Spare saddle", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    for form in re.findall(r"<form[^>]*>", html):
        if "/build/" in form:
            assert 'method="post"' in form and 'action="/bikes/' in form


# ---------------------------------------------------------------- add (palette)


def test_adding_from_the_palette_creates_a_default_named_part_and_returns_the_fragment(signed_in_client):
    bike = _bike()

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/add", {"component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 200
    assert response.text.lstrip().startswith('<div id="builder"')
    assert "<html" not in response.text
    assert _names(bike.id) == ["Frame"]
    assert "Frame" in response.text


def test_adding_without_htmx_redirects_back_to_the_builder(signed_in_client):
    bike = _bike()

    response = signed_in_client.post(
        f"/bikes/{bike.id}/build/add", data={"component_type": "frame", "target": f"bike:{bike.id}"},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/build"


def test_adding_before_a_sibling_orders_it(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    first = _mk("S1", "other", parent_component_id=wheel.id)

    _hx(signed_in_client, f"/bikes/{bike.id}/build/add",
        {"component_type": "other", "target": f"component:{wheel.id}", "before_component_id": str(first.id)})

    assert _names(bike.id) == ["Wheel", "Other part", "S1"]


def test_an_invalid_add_returns_the_fragment_with_a_422_and_the_reason(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/add",
                   {"component_type": "pedal", "target": f"component:{wheel.id}"})

    assert response.status_code == 422
    assert response.text.lstrip().startswith('<div id="builder"')
    assert 'role="alert"' in response.text
    assert "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert _names(bike.id) == ["Wheel"]


def test_an_invalid_add_without_htmx_renders_the_full_page_with_the_reason(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = signed_in_client.post(
        f"/bikes/{bike.id}/build/add", data={"component_type": "pedal", "target": f"component:{wheel.id}"}
    )

    assert response.status_code == 422 and "<html" in response.text
    assert "A pedal can be mounted on the bike" in response.text


@pytest.mark.parametrize(
    "data",
    [
        {"component_type": "flux-capacitor", "target": "bike:1"},
        {"component_type": "frame", "target": "storage"},
        {"component_type": "frame", "target": "bike:abc"},
        {"component_type": "", "target": "bike:1"},
        {"component_type": "frame"},
        {"component_type": "frame", "target": "bike:1", "before_component_id": "x"},
    ],
)
def test_malformed_add_requests_are_rejected_and_nothing_changes(signed_in_client, data):
    bike = _bike()

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/add", data)

    assert response.status_code == 422
    assert _names(bike.id) == []


def test_adding_onto_another_bike_is_refused(signed_in_client):
    bike = _bike("Mine")
    other = _bike("Other")

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/add", {"component_type": "frame", "target": f"bike:{other.id}"})

    assert response.status_code == 422
    assert _names(other.id) == []


def test_adding_a_second_single_instance_part_is_refused_with_the_existing_message(signed_in_client):
    bike = _bike()
    _mk("Frame", "frame", parent_bike_id=bike.id)

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/add", {"component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 422 and "already installed" in response.text


# ---------------------------------------------------------------- move / reorder / unmount


def test_mounting_a_storage_part_moves_it_onto_the_bike(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    hub = _mk("Hub", "hub")

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/move",
                   {"component_id": str(hub.id), "target": f"component:{wheel.id}"})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert component_service.get_component(hub.id).parent_component_id == wheel.id


def test_moving_a_mounted_part_to_storage(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    hub = _mk("Hub", "hub", parent_component_id=wheel.id)

    _hx(signed_in_client, f"/bikes/{bike.id}/build/move", {"component_id": str(hub.id), "target": "storage"})

    assert component_service.get_component(hub.id).parent_component_id is None


def test_reordering_siblings_persists_and_shows_on_the_bike_detail_page(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1, s2 = (_mk(n, "spoke", parent_component_id=wheel.id) for n in ("S1", "S2"))

    _hx(signed_in_client, f"/bikes/{bike.id}/build/move",
        {"component_id": str(s2.id), "target": f"component:{wheel.id}", "before_component_id": str(s1.id)})

    assert _names(bike.id) == ["Wheel", "S2", "S1"]
    detail = signed_in_client.get(f"/bikes/{bike.id}").text
    assert detail.index("S2") < detail.index("S1")
    assert signed_in_client.get(f"/bikes/{bike.id}/build").text.index("S2") < signed_in_client.get(f"/bikes/{bike.id}/build").text.index("S1")


def test_moving_a_part_with_its_subtree_keeps_the_subtree(signed_in_client):
    bike = _bike()
    w1 = _mk("W1", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=w1.id)
    tire = _mk("Tire", "tire", parent_component_id=rim.id)

    _hx(signed_in_client, f"/bikes/{bike.id}/build/move", {"component_id": str(rim.id), "target": "storage"})

    assert component_service.get_component(tire.id).parent_component_id == rim.id


def test_an_invalid_move_is_refused_with_the_reason_and_nothing_moves(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/move",
                   {"component_id": str(pedal.id), "target": f"component:{wheel.id}"})

    assert response.status_code == 422
    assert "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert component_service.get_component(pedal.id).parent_component_id is None


def test_dropping_a_part_into_its_own_subtree_is_refused(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/move",
                   {"component_id": str(wheel.id), "target": f"component:{rim.id}"})

    assert response.status_code == 422
    assert component_service.get_component(wheel.id).parent_bike_id == bike.id


def test_moving_a_part_that_belongs_to_another_bike_is_refused(signed_in_client):
    bike = _bike("Mine")
    other = _bike("Other")
    frame = _mk("Frame", "frame", parent_bike_id=other.id)

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/move", {"component_id": str(frame.id), "target": "storage"})

    assert response.status_code == 422
    assert component_service.get_component(frame.id).parent_bike_id == other.id


@pytest.mark.parametrize(
    "data",
    [
        {"component_id": "x", "target": "storage"},
        {"component_id": "1", "target": "nowhere"},
        {"component_id": "1"},
        {"component_id": "1", "target": "storage", "before_component_id": "-3"},
        {"component_id": "999", "target": "storage"},
    ],
)
def test_malformed_move_requests_are_rejected(signed_in_client, data):
    bike = _bike()
    _mk("Frame", "frame", parent_bike_id=bike.id)

    response = _hx(signed_in_client, f"/bikes/{bike.id}/build/move", data)

    assert response.status_code == 422
    assert _names(bike.id) == ["Frame"]


def test_a_move_without_htmx_redirects_back_to_the_builder(signed_in_client):
    bike = _bike()
    frame = _mk("Frame", "frame", parent_bike_id=bike.id)

    response = signed_in_client.post(
        f"/bikes/{bike.id}/build/move", data={"component_id": str(frame.id), "target": "storage"},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/build"


# ---------------------------------------------------------------- links


def test_the_bike_page_and_garage_card_link_to_the_builder(signed_in_client):
    bike = _bike()

    assert f'href="/bikes/{bike.id}/build"' in signed_in_client.get(f"/bikes/{bike.id}").text
    assert f'href="/bikes/{bike.id}/build"' in signed_in_client.get("/").text
