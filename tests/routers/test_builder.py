"""The unified bike and part screen and its actions (specs/005-unified-bike-screen, M2)."""

import re

import pytest

from app.models import component_kinds
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
                        ("Schedules", "/schedules"), ("Rides", "/rides"),
                        ("Pair with Strava", "/strava-pairing")):
        assert f'href="/bikes/{bike.id}{href}">{label}</a>' in html
    assert "Delete bike" not in html and "Delete this bike" not in html  # moved to the Edit screen (specs/029)


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


def test_bike_root_is_a_drop_target_that_has_no_accept_list(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    root = re.search(r'<div class="builder-root drop-target"[^>]*>', html).group(0)
    assert f'data-ref="bike:{bike.id}"' in root and "data-accepts" not in root
    assert "Drag a frame here to start" in html


def test_tree_nodes_are_draggable_drop_targets(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    node = re.search(rf'<div class="node-row drop-target"[^>]*data-id="{wheel.id}"[^>]*>', html).group(0)
    assert 'draggable="true"' in node and 'data-source="node"' in node and 'data-type="wheel"' in node
    assert f'data-ref="component:{wheel.id}"' in node and f'data-parent-ref="bike:{bike.id}"' in node
    assert "data-accepts" not in node  # any part can be dropped on any part


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
    palette = re.findall(r'data-source="palette" data-type="([a-z_]+)"', html)
    assert palette == list(component_kinds.COMPONENT_TYPES)  # every offered kind, in category order
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


def test_part_rows_have_only_garage_and_trash_actions(signed_in_client):
    # 041: no reorder arrows and no Move to…; moving and reordering are by drag and drop.
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("S1", "other", parent_component_id=wheel.id)
    _mk("S2", "other", parent_component_id=wheel.id)
    _mk("Spare tire", "tire")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert "node-more" not in html and "Move S1" not in html and "Move S2" not in html and "to…" not in html.split('class="builder-tree"')[1].split('class="builder-side"')[0]
    tree = html.split('class="builder-tree"')[1].split('class="builder-side"')[0]
    for row in re.findall(r'<span class="node-actions">(.*?)</span>\s*</div>', tree, re.S):
        labels = re.findall(r'aria-label="([^"]+)"', row)
        assert [l.split(" ")[0] for l in labels] == ["Garage", "Trash"], labels


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
                        ("Schedules", "/schedules"), ("Rides", "/rides")):
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


def test_adding_a_palette_part_to_the_storage_box_creates_it_in_storage(signed_in_client):
    bike = _bike()

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), "component_type": "saddle", "target": "storage"})

    assert response.status_code == 200
    assert [c.name for c in component_service.list_in_storage()] == ["Saddle"]
    assert _names(bike.id) == []
    assert "Saddle" in response.text and 'data-source="storage"' in response.text  # shows in the box


def test_storage_add_works_from_a_part_screen_and_keeps_that_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add",
                   {"root": f"component:{wheel.id}", "component_type": "tire", "target": "storage"})

    assert response.status_code == 200 and f'data-root="component:{wheel.id}"' in response.text
    assert [c.component_type for c in component_service.list_in_storage()] == ["tire"]


def test_a_wheel_screen_offers_the_whole_palette(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    assert len(re.findall(r'data-source="palette" data-type="([a-z_]+)"', html)) == 34


def test_adding_before_a_sibling_orders_it(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    first = _mk("S1", "tube", parent_component_id=wheel.id)

    _hx(signed_in_client, "/builder/add",
        {"root": _root(bike), "component_type": "tube", "target": f"component:{wheel.id}", "before_component_id": str(first.id)})

    assert _names(bike.id) == ["Wheel", "Tube", "S1"]


def test_a_part_of_any_kind_can_be_added_to_a_wheel(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add",
                   {"root": _root(bike), "component_type": "pedal", "target": f"component:{wheel.id}"})

    assert response.status_code == 200
    assert _names(bike.id) == ["Wheel", "Pedals"]


def test_an_add_of_a_kind_that_is_not_offered_returns_the_fragment_with_a_422(signed_in_client):
    bike = _bike()

    response = _hx(signed_in_client, "/builder/add",
                   {"root": _root(bike), "component_type": "rim", "target": f"bike:{bike.id}"})

    assert response.status_code == 422
    assert response.text.lstrip().startswith('<div id="builder"') and 'role="alert"' in response.text
    assert _names(bike.id) == []


def test_an_unoffered_add_without_htmx_renders_the_full_page_with_the_reason(signed_in_client):
    bike = _bike()

    response = signed_in_client.post(
        "/builder/add", data={"root": _root(bike), "component_type": "rim", "target": f"bike:{bike.id}"}
    )

    assert response.status_code == 422 and "<html" in response.text


@pytest.mark.parametrize(
    "data",
    [
        {"component_type": "flux-capacitor", "target": "bike:1"},
        {"component_type": "rim", "target": "bike:1"},  # older finer kinds are never offered
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


def test_a_second_part_of_the_same_kind_can_be_added(signed_in_client):
    bike = _bike()
    _mk("Frame", "frame", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/add", {"root": _root(bike), "component_type": "frame", "target": f"bike:{bike.id}"})

    assert response.status_code == 200 and _names(bike.id) == ["Frame", "Frame"]


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


def test_a_part_can_be_moved_onto_any_other_part(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    response = _hx(signed_in_client, "/builder/move",
                   {"root": _root(bike), "component_id": str(pedal.id), "target": f"component:{wheel.id}"})

    assert response.status_code == 200
    assert component_service.get_component(pedal.id).parent_component_id == wheel.id


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


def test_trash_always_asks_first_with_a_keep_history_checkbox(signed_in_client):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(saddle.id)})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert 'class="confirm"' in response.text and "Delete Saddle?" in response.text
    assert re.search(r'<input[^>]*type="checkbox"[^>]*name="keep_history"', response.text)
    assert not re.search(r'name="keep_history"[^>]*\bchecked\b', response.text)  # unchecked by default
    assert "Keep install history" in response.text and "Cancel" in response.text
    assert component_service.get_component(saddle.id) is not None  # nothing deleted yet


def test_confirming_without_the_box_deletes_the_part_and_its_history_everywhere(signed_in_client):
    from app.services import component_history_service as history

    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/delete",
                   {"root": _root(bike), "component_id": str(tire.id), "confirmed": "true"})

    assert response.status_code == 200 and component_service.get_component(tire.id) is None
    assert history.list_history(tire.id) == []
    page = signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    assert "Tire" not in page.split("<tbody>")[1] and "Wheel" in page  # the wheel's own row remains


def test_confirming_with_the_box_keeps_the_history_labeled_deleted(signed_in_client):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    _hx(signed_in_client, "/builder/delete",
        {"root": _root(bike), "component_id": str(saddle.id), "confirmed": "true", "keep_history": "on"})

    page = signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    assert "Saddle (deleted)" in " ".join(re.sub(r"<[^>]+>", " ", page).split())


def test_deleting_a_part_keeps_its_sub_parts_history(signed_in_client):
    from app.services import component_history_service as history

    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    _hx(signed_in_client, "/builder/delete",
        {"root": _root(bike), "component_id": str(wheel.id), "confirmed": "true"})

    assert component_service.get_component(tire.id) is not None and history.list_history(tire.id) != []


def test_trash_asks_in_place_when_there_are_sub_parts_and_says_they_move_to_storage(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/delete", {"root": _root(bike), "component_id": str(wheel.id)})

    assert response.status_code == 200 and response.text.lstrip().startswith('<div id="builder"')
    assert 'class="confirm"' in response.text and "Delete Wheel?" in response.text and "move to storage" in response.text
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


def test_confirming_deletes_the_part_and_keeps_its_sub_parts_in_storage(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = _hx(signed_in_client, "/builder/delete",
                   {"root": _root(bike), "component_id": str(wheel.id), "confirmed": "true"})

    assert response.status_code == 200 and 'class="confirm"' not in response.text
    assert component_service.get_component(wheel.id) is None
    kept = component_service.get_component(tire.id)
    assert kept is not None and (kept.parent_bike_id, kept.parent_component_id) == (None, None)
    assert "Tire" in response.text  # now listed in the storage box


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

    response = _hx(signed_in_client, "/builder/delete", {"root": f"component:{saddle.id}", "component_id": str(saddle.id), "confirmed": "true"})

    assert response.headers["hx-redirect"] == f"/bikes/{bike.id}"
    assert component_service.get_component(saddle.id) is None


def test_trashing_a_nested_part_itself_goes_up_to_its_parent_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    response = signed_in_client.post(
        "/builder/delete", data={"root": f"component:{tire.id}", "component_id": str(tire.id), "confirmed": "true"}, follow_redirects=False
    )

    assert response.status_code == 303 and response.headers["location"] == f"/components/{wheel.id}"


def test_trashing_a_stored_part_itself_goes_to_storage(signed_in_client):
    spare = _mk("Spare saddle", "saddle")

    response = _hx(signed_in_client, "/builder/delete", {"root": f"component:{spare.id}", "component_id": str(spare.id), "confirmed": "true"})

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


# ---------------------------------------------------------------- icons on the screen (specs/006, M2)


def test_tree_rows_palette_and_storage_items_show_their_part_icons(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)
    _mk("Spare saddle", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    rows = re.findall(r'<div class="node-row drop-target".*?</div>', html, re.S)
    assert len(rows) == 2 and all('class="icon part-icon"' in r for r in rows)
    palette = re.findall(r'<li class="side-item"[^>]*data-source="palette".*?</li>', html, re.S)
    assert palette and all('class="icon part-icon"' in p for p in palette)
    storage = re.search(r'<li class="side-item"[^>]*data-source="storage".*?</li>', html, re.S).group(0)
    assert 'class="icon part-icon"' in storage


def test_garage_bike_cards_and_storage_cards_use_the_new_icons(signed_in_client):
    _bike()
    _mk("Spare saddle", "saddle")

    garage = signed_in_client.get("/").text
    storage = signed_in_client.get("/components").text

    assert garage.count("<circle") >= 2  # the bike drawing: two wheels
    assert 'class="icon part-icon"' in storage or 'class="icon"' in storage


# ------------------------------------------------ specs/028: stored part names are links


def _storage_card(html):
    """The In storage section: the last collapsible section of the Add a part panel (specs/033)."""
    return re.search(r'<details class="palette-category storage-drop.*?</details>\s*</section>', html, re.S).group(0)


def test_stored_part_names_link_to_the_part_on_a_bike_screen(signed_in_client):
    bike = _bike()
    spare = _mk("Spare tire", "tire")

    card = _storage_card(signed_in_client.get(f"/bikes/{bike.id}").text)

    assert f'<a class="node-name" href="/components/{spare.id}">Spare tire</a>' in card
    assert '</a> <span class="chip">Tire</span>' in " ".join(card.split())  # the chip stays outside the link


def test_stored_part_names_link_on_a_part_screen_too(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    spare = _mk("Spare saddle", "saddle")

    card = _storage_card(signed_in_client.get(f"/components/{wheel.id}").text)

    assert f'<a class="node-name" href="/components/{spare.id}">Spare saddle</a>' in card


def test_the_storage_card_still_drags_and_still_has_its_add_to_control(signed_in_client):
    bike = _bike()
    spare = _mk("Spare tire", "tire")

    card = _storage_card(signed_in_client.get(f"/bikes/{bike.id}").text)

    assert re.search(rf'<li class="side-item"[^>]*draggable="true"[^>]*data-source="storage"[^>]*data-id="{spare.id}"', card)
    assert 'action="/builder/move"' in card and ">Add to…</summary>" in card


def test_the_linked_part_opens_with_the_garage_storage_breadcrumb(signed_in_client):
    bike = _bike()
    spare = _mk("Spare tire", "tire")
    assert f'href="/components/{spare.id}"' in _storage_card(signed_in_client.get(f"/bikes/{bike.id}").text)

    html = signed_in_client.get(f"/components/{spare.id}").text

    crumbs = re.search(r'<nav[^>]*aria-label="Breadcrumb".*?</nav>', html, re.S).group(0)
    assert '<a href="/">Garage</a>' in crumbs and '<a href="/components">Storage</a>' in crumbs
    assert 'aria-current="page"><span>Spare tire</span>' in crumbs


# ------------------------------------------------ specs/033: Add a part panel with storage


def _panel(html):
    return re.search(r'<section class="side-section" aria-labelledby="palette-heading">.*?</section>', html, re.S).group(0)


def test_there_is_one_side_panel_titled_add_a_part(signed_in_client):
    bike = _bike()
    _mk("Spare", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert '<h2 id="palette-heading">Add a part</h2>' in html
    assert "Add a new part" not in html
    assert not re.search(r"<h2[^>]*>\s*In storage", html)  # the separate card is gone
    assert len(re.findall(r'<section class="side-section', html)) == 1


def test_storage_is_the_last_collapsed_section_after_the_five_categories(signed_in_client):
    bike = _bike()
    _mk("Spare saddle", "saddle")
    _mk("Spare tire", "tire")

    panel = _panel(signed_in_client.get(f"/bikes/{bike.id}").text)

    summaries = re.findall(r'<details class="palette-category[^"]*"([^>]*)>\s*<summary>([^<]*)</summary>', panel)
    assert [name for _, name in summaries] == [*component_kinds.CATEGORIES, "In storage (2)"]
    assert all("open" not in attrs.split() for attrs, _ in summaries)  # all collapsed on load


def test_the_storage_section_is_still_the_drop_target(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    section = re.search(r'<details class="palette-category storage-drop drop-target"[^>]*>', html).group(0)
    assert 'data-ref="storage"' in section


def test_stored_parts_keep_their_rows_link_drag_and_add_to(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    spare = _mk("Spare tire", "tire")

    section = _storage_card(signed_in_client.get(f"/bikes/{bike.id}").text)

    assert re.search(rf'<li class="side-item"[^>]*draggable="true"[^>]*data-source="storage"[^>]*data-id="{spare.id}"', section)
    assert f'<a class="node-name" href="/components/{spare.id}">Spare tire</a>' in section
    assert 'action="/builder/move"' in section and ">Add to…</summary>" in section
    assert f'value="component:{wheel.id}"' in section  # a place for it


def test_a_part_screen_shows_the_storage_count_in_the_panel(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Spare", "saddle")

    html = signed_in_client.get(f"/components/{wheel.id}").text

    assert "In storage (1)" in html


def test_empty_storage_reads_zero_and_has_the_drag_hint(signed_in_client):
    bike = _bike()

    section = _storage_card(signed_in_client.get(f"/bikes/{bike.id}").text)

    assert "In storage (0)" in section
    assert "Nothing in storage. Drag a part here to take it off." in section


def test_the_palette_is_unchanged_by_the_storage_section(signed_in_client):
    bike = _bike()
    _mk("Spare", "saddle")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    types = re.findall(r'draggable="true" data-source="palette" data-type="([a-z_]+)"', html)
    assert types == list(component_kinds.COMPONENT_TYPES)


def test_the_same_panel_shows_on_a_part_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    assert '<h2 id="palette-heading">Add a part</h2>' in html and "In storage (0)" in html
