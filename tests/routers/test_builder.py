"""The unified bike and part screen and its actions (specs/005-unified-bike-screen, M2)."""

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


def _root(bike):
    return f"bike:{bike.id}"


def _attr(html, pattern):
    return re.search(pattern, html, re.S)


# ---------------------------------------------------------------- auth / 404


@pytest.mark.parametrize(
    "method,path",
    [("post", "/builder/add"), ("post", "/builder/move"), ("post", "/builder/delete"),
     ("get", "/bikes/1"), ("get", "/components/1"), ("get", "/bikes/1/build")],
)
def test_routes_require_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_missing_bike_or_part_screens_are_404(signed_in_client):
    assert signed_in_client.get("/bikes/99").status_code == 404
    assert signed_in_client.get("/components/99").status_code == 404
    assert _hx(signed_in_client, "/builder/add", {"root": "bike:99", "component_type": "frame", "target": "bike:99"}).status_code == 404


def test_the_old_build_address_lands_on_the_bike_screen(signed_in_client):
    bike = _bike()

    response = signed_in_client.get(f"/bikes/{bike.id}/build", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}")


# ---------------------------------------------------------------- the bike screen


def test_bike_screen_combines_breadcrumb_actions_tree_storage_and_palette(signed_in_client):
    bike = _bike("2022 Trek Domane")
    frame = _mk("Frame", "frame", parent_bike_id=bike.id)
    _mk("Spare saddle", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert _attr(html, r'<nav class="breadcrumb" aria-label="Breadcrumb">.*?<a href="/">Garage</a>.*?aria-current="page"><span>2022 Trek Domane</span>')
    assert '<div id="builder" class="builder"' in html and f'data-root="bike:{bike.id}"' in html
    assert html.index('class="builder-tree"') < html.index('class="builder-side"')
    assert f'data-id="{frame.id}"' in html and "Spare saddle" in html
    assert 'builder.js' in html


def test_bike_screen_has_the_bike_actions_including_pair_with_strava(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    for label, href in (("Edit", "/edit"), ("Maintenance history", "/maintenance"),
                        ("Add schedule", "/schedules/new"), ("Adjust mileage", "/mileage/adjust"),
                        ("Pair with Strava", "/strava-pairing")):
        assert f'href="/bikes/{bike.id}{href}">{label}</a>' in html
    assert "Delete bike" in html


def test_pair_with_strava_disappears_once_paired(signed_in_client):
    bike = _bike()
    bike_service.pair_to_strava_gear  # noqa: B018 (exists)
    from app.db import connection

    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET strava_gear_id = 'g1' WHERE id = ?", (bike.id,))

    assert "Pair with Strava" not in signed_in_client.get(f"/bikes/{bike.id}").text


def test_there_is_no_build_or_add_component_button_anywhere(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    pages = [f"/bikes/{bike.id}", f"/components/{wheel.id}", "/"]
    for path in pages:
        html = signed_in_client.get(path).text
        assert not re.search(r"/bikes/\d+/build", html), path
        assert ">Build<" not in html and "Start building" not in html, path
        assert "Add component</a>" not in html, path


def test_bike_root_is_a_drop_target_with_its_accepted_types(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    root = re.search(r'<div class="builder-root drop-target"[^>]*>', html).group(0)
    assert f'data-ref="bike:{bike.id}"' in root
    accepts = re.search(r'data-accepts="([^"]*)"', root).group(1).split()
    assert {"frame", "wheel", "brake", "pedal"} <= set(accepts) and "tire" not in accepts
    assert "Drag a frame here to start" in html


def test_tree_nodes_are_draggable_drop_targets_with_rules_attached(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    node = re.search(rf'<div class="node-row drop-target"[^>]*data-id="{wheel.id}"[^>]*>', html).group(0)
    assert 'draggable="true"' in node and 'data-source="node"' in node and 'data-type="wheel"' in node
    assert f'data-ref="component:{wheel.id}"' in node and f'data-parent-ref="bike:{bike.id}"' in node
    accepts = re.search(r'data-accepts="([^"]*)"', node).group(1).split()
    assert "other" in accepts and "tire" not in accepts  # the single tire slot is taken


def test_every_part_row_has_garage_and_trash_buttons(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    for part in (wheel, tire):
        garage = _attr(html, rf'<form class="node-form"[^>]*action="/builder/move"(?:(?!</form>).)*name="component_id" value="{part.id}"(?:(?!</form>).)*name="target" value="storage"(?:(?!</form>).)*aria-label="Garage {part.name}')
        trash = _attr(html, rf'<form class="node-form"[^>]*action="/builder/delete"(?:(?!</form>).)*name="component_id" value="{part.id}"(?:(?!</form>).)*aria-label="Trash {part.name}"')
        assert garage and trash, part.name


def test_storage_and_palette_items_are_draggable_sources(signed_in_client):
    bike = _bike()
    spare = _mk("Spare tire", "tire")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert re.search(rf'<li class="side-item"[^>]*draggable="true"[^>]*data-source="storage"[^>]*data-id="{spare.id}"', html)
    palette = re.findall(r'data-source="palette" data-type="([a-z]+)"', html)
    assert palette == ["frame", "fork", "wheel", "tire", "brake", "drivetrain", "chain", "pedal",
                       "saddle", "handlebar", "other"]
    assert 'data-ref="storage"' in html


def test_every_drag_action_has_a_form_with_only_valid_targets(signed_in_client):
    bike = _bike("Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Spare tire", "tire")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    move_forms = re.findall(r'<form class="side-form"[^>]*action="/builder/move".*?</form>', html, re.S)
    assert move_forms and f'value="component:{wheel.id}"' in move_forms[0]
    assert 'name="root"' in move_forms[0] and 'name="component_id"' in move_forms[0] and 'name="target"' in move_forms[0]
    add_forms = re.findall(r'<form class="side-form"[^>]*action="/builder/add".*?</form>', html, re.S)
    assert any('name="component_type" value="tire"' in f and f'value="component:{wheel.id}"' in f for f in add_forms)
    assert not any('value="rim"' in f for f in add_forms)


def test_reorder_buttons_exist_for_siblings(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1 = _mk("S1", "other", parent_component_id=wheel.id)
    s2 = _mk("S2", "other", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert 'aria-label="Move S2 up"' in html and 'aria-label="Move S1 down"' in html
    assert 'aria-label="Move S1 up"' not in html and 'aria-label="Move S2 down"' not in html
    up = re.search(r'<form class="node-form"[^>]*>(?:(?!</form>).)*aria-label="Move S2 up".*?</form>', html, re.S).group(0)
    assert f'name="before_component_id" value="{s1.id}"' in up and f'name="component_id" value="{s2.id}"' in up


def test_every_form_has_a_plain_post_action(signed_in_client):
    bike = _bike()
    _mk("Spare saddle", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    for form in re.findall(r"<form[^>]*>", html):
        if "/builder/" in form:
            assert 'method="post"' in form and 'action="/builder/' in form


# ---------------------------------------------------------------- the part screen (drill-down)


def test_part_screen_has_the_trail_its_own_actions_and_no_pair_with_strava(signed_in_client):
    bike = _bike("Road")
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/components/{tire.id}").text

    crumbs = re.search(r'<nav class="breadcrumb".*?</nav>', html, re.S).group(0)
    assert re.findall(r"<(?:a href=\"([^\"]+)\"|span)>", crumbs) == ["/", f"/bikes/{bike.id}", f"/components/{wheel.id}", ""]
    assert 'aria-current="page"><span>Tire</span>' in crumbs
    for label, href in (("Edit", "/edit"), ("Maintenance history", "/maintenance"),
                        ("Add schedule", "/schedules/new"), ("Adjust mileage", "/mileage/adjust")):
        assert f'href="/components/{tire.id}{href}">{label}</a>' in html
    assert "Pair with Strava" not in html
    assert "Delete bike" not in html


def test_part_screen_is_the_same_layout_scoped_to_its_sub_parts(signed_in_client):
    bike = _bike()
    front = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear wheel", "wheel", parent_bike_id=bike.id)
    _mk("Front tire", "tire", parent_component_id=front.id)
    _mk("Rear tire", "tire", parent_component_id=rear.id)

    html = signed_in_client.get(f"/components/{front.id}").text

    assert f'data-root="component:{front.id}"' in html
    assert "Front tire" in html and "Rear tire" not in html
    assert 'class="builder-tree"' in html and 'class="builder-side"' in html


def test_part_header_has_garage_and_trash_buttons(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    header = re.search(r'<div class="actions panel part-actions">.*?</div>', html, re.S).group(0)
    assert "Garage</button>" in header and "Trash</button>" in header
    assert f'name="root" value="component:{wheel.id}"' in header


def test_a_stored_part_shows_the_storage_trail_and_no_garage_button(signed_in_client):
    spare = _mk("Spare wheel", "wheel")

    html = signed_in_client.get(f"/components/{spare.id}").text

    assert 'href="/components">Storage</a>' in html
    header = re.search(r'<div class="actions panel part-actions">.*?</div>', html, re.S).group(0)
    assert "Garage</button>" not in header and "Trash</button>" in header


def test_a_part_screen_without_sub_parts_says_so(signed_in_client):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    assert "Nothing mounted on this part yet" in signed_in_client.get(f"/components/{saddle.id}").text


# ---------------------------------------------------------------- add (palette)


def test_adding_from_the_palette_creates_a_default_named_part_and_returns_the_fragment(signed_in_client):
    bike = _bike()

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), "component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 200
    assert response.text.lstrip().startswith('<div id="builder"') and "<html" not in response.text
    assert _names(bike.id) == ["Frame"] and "Frame" in response.text


def test_adding_without_htmx_redirects_back_to_the_screen(signed_in_client):
    bike = _bike()

    response = signed_in_client.post(
        "/builder/add", data={"root": _root(bike), "component_type": "frame", "target": f"bike:{bike.id}"},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}"


def test_adding_inside_a_part_screen_returns_that_parts_fragment(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add",
                   {"root": f"component:{wheel.id}", "component_type": "tire", "target": f"component:{wheel.id}"})

    assert response.status_code == 200 and f'data-root="component:{wheel.id}"' in response.text
    assert "Tire" in response.text and _names(bike.id) == ["Wheel", "Tire"]


def test_adding_before_a_sibling_orders_it(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    first = _mk("S1", "other", parent_component_id=wheel.id)

    _hx(signed_in_client, "/builder/add",
        {"root": _root(bike), "component_type": "other", "target": f"component:{wheel.id}", "before_component_id": str(first.id)})

    assert _names(bike.id) == ["Wheel", "Other part", "S1"]


def test_an_invalid_add_returns_the_fragment_with_a_422_and_the_reason(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add",
                   {"root": _root(bike), "component_type": "pedal", "target": f"component:{wheel.id}"})

    assert response.status_code == 422
    assert response.text.lstrip().startswith('<div id="builder"') and 'role="alert"' in response.text
    assert "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert _names(bike.id) == ["Wheel"]


def test_an_invalid_add_without_htmx_renders_the_full_page_with_the_reason(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = signed_in_client.post(
        "/builder/add", data={"root": _root(bike), "component_type": "pedal", "target": f"component:{wheel.id}"}
    )

    assert response.status_code == 422 and "<html" in response.text and "A pedal can be mounted on the bike" in response.text


@pytest.mark.parametrize(
    "data",
    [
        {"component_type": "flux-capacitor", "target": "bike:1"},
        {"component_type": "rim", "target": "bike:1"},  # older finer kinds are never offered
        {"component_type": "frame", "target": "storage"},
        {"component_type": "frame", "target": "bike:abc"},
        {"component_type": "", "target": "bike:1"},
        {"component_type": "frame"},
        {"component_type": "frame", "target": "bike:1", "before_component_id": "x"},
    ],
)
def test_malformed_add_requests_are_rejected_and_nothing_changes(signed_in_client, data):
    bike = _bike()

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), **data})

    assert response.status_code == 422 and _names(bike.id) == []


@pytest.mark.parametrize("root", ["", "bike", "bike:x", "wheel:1", "bike:1;2", "bike:-1"])
def test_a_malformed_root_is_refused(signed_in_client, root):
    bike = _bike()

    response = _hx(signed_in_client, "/builder/add", {"root": root, "component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 404 and _names(bike.id) == []


def test_adding_outside_the_screens_scope_is_refused(signed_in_client):
    bike = _bike("Mine")
    other = _bike("Other")

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), "component_type": "frame", "target": f"bike:{other.id}"})

    assert response.status_code == 422 and _names(other.id) == []


def test_a_second_single_instance_part_is_refused_with_the_existing_message(signed_in_client):
    bike = _bike()
    _mk("Frame", "frame", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), "component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 422 and "already installed" in response.text


# ---------------------------------------------------------------- move / reorder / unmount


def test_mounting_a_storage_part_moves_it_onto_the_bike(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire")

    response = _hx(signed_in_client, "/builder/move",
                   {"root": _root(bike), "component_id": str(tire.id), "target": f"component:{wheel.id}"})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert component_service.get_component(tire.id).parent_component_id == wheel.id


def test_garage_moves_a_part_with_its_subtree_to_storage(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    _hx(signed_in_client, "/builder/move", {"root": _root(bike), "component_id": str(wheel.id), "target": "storage"})

    assert component_service.get_component(wheel.id).parent_bike_id is None
    assert component_service.get_component(tire.id).parent_component_id == wheel.id  # subtree intact


def test_garage_on_the_part_itself_reloads_its_screen_with_the_storage_trail(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    root = f"component:{wheel.id}"

    htmx = _hx(signed_in_client, "/builder/move", {"root": root, "component_id": str(wheel.id), "target": "storage"})

    assert htmx.status_code == 200 and htmx.headers["hx-redirect"] == f"/components/{wheel.id}"
    assert component_service.get_component(wheel.id).parent_bike_id is None
    assert 'href="/components">Storage</a>' in signed_in_client.get(f"/components/{wheel.id}").text


def test_reordering_siblings_persists_and_shows_on_the_bike_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1, s2 = (_mk(n, "other", parent_component_id=wheel.id) for n in ("S1", "S2"))

    _hx(signed_in_client, "/builder/move",
        {"root": _root(bike), "component_id": str(s2.id), "target": f"component:{wheel.id}", "before_component_id": str(s1.id)})

    assert _names(bike.id) == ["Wheel", "S2", "S1"]
    html = signed_in_client.get(f"/bikes/{bike.id}").text
    assert html.index("S2") < html.index("S1")


def test_an_invalid_move_is_refused_with_the_reason_and_nothing_moves(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = _hx(signed_in_client, "/builder/move",
                   {"root": _root(bike), "component_id": str(pedal.id), "target": f"component:{wheel.id}"})

    assert response.status_code == 422 and "A pedal can be mounted on the bike, not on a wheel." in response.text
    assert component_service.get_component(pedal.id).parent_component_id is None


def test_dropping_a_part_into_its_own_subtree_is_refused(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/move",
                   {"root": _root(bike), "component_id": str(wheel.id), "target": f"component:{tire.id}"})

    assert response.status_code == 422 and component_service.get_component(wheel.id).parent_bike_id == bike.id


def test_moving_a_part_that_belongs_to_another_bike_is_refused(signed_in_client):
    bike = _bike("Mine")
    other = _bike("Other")
    frame = _mk("Frame", "frame", parent_bike_id=other.id)

    response = _hx(signed_in_client, "/builder/move", {"root": _root(bike), "component_id": str(frame.id), "target": "storage"})

    assert response.status_code == 422 and component_service.get_component(frame.id).parent_bike_id == other.id


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

    response = _hx(signed_in_client, "/builder/move", {"root": _root(bike), **data})

    assert response.status_code == 422 and _names(bike.id) == ["Frame"]


def test_a_move_without_htmx_redirects_back_to_the_screen(signed_in_client):
    bike = _bike()
    frame = _mk("Frame", "frame", parent_bike_id=bike.id)

    response = signed_in_client.post(
        "/builder/move", data={"root": _root(bike), "component_id": str(frame.id), "target": "storage"},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}"


# ---------------------------------------------------------------- trash (delete in place)


def test_trash_deletes_a_part_with_no_dependants_at_once(signed_in_client):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(saddle.id)})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert component_service.get_component(saddle.id) is None
    assert f'data-id="{saddle.id}"' not in response.text  # gone from the tree


def test_trash_asks_in_place_when_there_are_sub_parts_and_names_what_goes(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(wheel.id)})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert 'class="confirm"' in response.text and "Delete Wheel?" in response.text and "sub-tree" in response.text
    assert 'name="confirmed" value="true"' in response.text and "Cancel" in response.text
    assert component_service.get_component(wheel.id) is not None


def test_trash_asks_when_the_part_has_maintenance_history(signed_in_client):
    from app.services import maintenance_service

    bike = _bike()
    chain = _mk("Chain", "chain", parent_bike_id=bike.id)
    maintenance_service.log_maintenance(component_id=chain.id, description="Waxed", performed_at="2026-05-01")

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(chain.id)})

    assert 'class="confirm"' in response.text and "maintenance history" in response.text
    assert component_service.get_component(chain.id) is not None


def test_confirming_deletes_the_part_and_its_sub_parts(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/delete",
                   {"root": _root(bike), "component_id": str(wheel.id), "confirmed": "true"})

    assert response.status_code == 200 and 'class="confirm"' not in response.text
    assert component_service.get_component(wheel.id) is None and component_service.get_component(tire.id) is None


def test_trash_without_htmx_still_asks_on_a_full_page_and_then_redirects(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    ask = signed_in_client.post("/builder/delete", data={"root": _root(bike), "component_id": str(wheel.id)})
    done = signed_in_client.post(
        "/builder/delete", data={"root": _root(bike), "component_id": str(wheel.id), "confirmed": "true"},
        follow_redirects=False,
    )

    assert "<html" in ask.text and 'class="confirm"' in ask.text
    assert done.status_code == 303 and done.headers["location"] == f"/bikes/{bike.id}"


def test_trashing_the_part_itself_goes_up_to_the_bike(signed_in_client):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": f"component:{saddle.id}", "component_id": str(saddle.id)})

    assert response.headers["hx-redirect"] == f"/bikes/{bike.id}"
    assert component_service.get_component(saddle.id) is None


def test_trashing_a_nested_part_itself_goes_up_to_its_parent_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = signed_in_client.post(
        "/builder/delete", data={"root": f"component:{tire.id}", "component_id": str(tire.id)}, follow_redirects=False
    )

    assert response.status_code == 303 and response.headers["location"] == f"/components/{wheel.id}"


def test_trashing_a_stored_part_itself_goes_to_storage(signed_in_client):
    spare = _mk("Spare saddle", "saddle")

    response = _hx(signed_in_client, "/builder/delete", {"root": f"component:{spare.id}", "component_id": str(spare.id)})

    assert response.headers["hx-redirect"] == "/components"


def test_trash_outside_the_screens_scope_is_refused(signed_in_client):
    bike = _bike("Mine")
    other = _bike("Other")
    frame = _mk("Frame", "frame", parent_bike_id=other.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(frame.id)})

    assert response.status_code == 422 and component_service.get_component(frame.id) is not None


@pytest.mark.parametrize("data", [{"component_id": "x"}, {"component_id": "0"}, {}])
def test_malformed_trash_requests_are_rejected(signed_in_client, data):
    bike = _bike()
    _mk("Frame", "frame", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), **data})

    assert response.status_code == 422 and _names(bike.id) == ["Frame"]


# ---------------------------------------------------------------- garage links


def test_garage_cards_open_the_bike_and_have_no_build_or_add_component(signed_in_client):
    bike = _bike()

    html = signed_in_client.get("/").text

    assert f'href="/bikes/{bike.id}">View</a>' in html
    assert not re.search(r"/bikes/\d+/build", html) and "Add component</a>" not in html
