"""View model for the interactive builder (specs/004-bike-builder, M3)."""

import pytest

from app.db import connection
from app.services import bike_service, builder_service, component_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def _view(bike):
    return builder_service.build_view(bike.id)


def test_unknown_bike_has_no_view(db_path):
    assert builder_service.build_view(999) is None


def test_empty_bike_accepts_bike_level_parts_and_has_no_nodes(db_path):
    bike = bike_service.create_bike(name="Road")

    view = _view(bike)

    assert view.nodes == []
    assert view.root_ref == f"bike:{bike.id}"
    assert {"frame", "wheel", "fork", "brake", "pedal"} <= set(view.root_accepts)
    assert "tire" not in view.root_accepts


def test_root_accepts_excludes_single_instance_types_already_present(db_path):
    bike = bike_service.create_bike(name="Road")
    _mk("Frame", "frame", parent_bike_id=bike.id)
    _mk("Wheel", "wheel", parent_bike_id=bike.id)

    accepts = _view(bike).root_accepts

    assert "frame" not in accepts  # single-instance slot taken
    assert "wheel" in accepts and "other" in accepts  # several wheels (front/rear) are fine


def test_nodes_nest_in_position_order_with_per_node_accepts(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    _mk("Valve", "other", parent_component_id=wheel.id)

    view = _view(bike)

    assert [n.component.name for n in view.nodes] == ["Wheel"]
    wheel_node = view.nodes[0]
    assert [c.component.name for c in wheel_node.children] == ["Tire", "Valve"]
    assert wheel_node.ref == f"component:{wheel.id}"
    assert wheel_node.parent_ref == f"bike:{bike.id}"
    assert "tire" not in wheel_node.accepts  # the single tire slot is taken
    assert "other" in wheel_node.accepts  # multi
    assert "pedal" not in wheel_node.accepts
    assert tire.id == wheel_node.children[0].component.id


def test_move_controls_list_only_valid_targets_on_this_bike(db_path):
    bike = bike_service.create_bike(name="Road")
    other = bike_service.create_bike(name="Other")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Wheel", "wheel", parent_bike_id=other.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    node = _view(bike).nodes[0].children[0]

    assert node.component.id == tire.id
    assert [t.value for t in node.targets] == ["storage"]  # the other bike's wheel is not offered here


def test_reorder_controls_point_at_neighbours(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1, s2, s3 = (_mk(n, "other", parent_component_id=wheel.id) for n in ("S1", "S2", "S3"))

    nodes = {n.component.name: n for n in _view(bike).nodes[0].children}

    assert (nodes["S1"].can_up, nodes["S1"].can_down, nodes["S1"].down_before) == (False, True, s3.id)
    assert (nodes["S2"].can_up, nodes["S2"].up_before, nodes["S2"].can_down) == (True, s1.id, True)
    assert nodes["S2"].down_before is None  # moving down from the middle lands last
    assert (nodes["S3"].can_up, nodes["S3"].up_before, nodes["S3"].can_down) == (True, s2.id, False)


def test_storage_items_offer_add_targets_on_this_bike(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    spare = _mk("Spare tire", "tire")
    _mk("Spare saddle", "saddle")

    view = _view(bike)

    by_name = {item.component.name: item for item in view.storage}
    assert [t.value for t in by_name["Spare tire"].targets] == [f"component:{wheel.id}"]
    assert [t.value for t in by_name["Spare saddle"].targets] == [f"bike:{bike.id}"]
    assert spare.id == by_name["Spare tire"].component.id


def test_palette_lists_only_the_offered_part_types_with_their_valid_targets(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    palette = {p.type: p for p in _view(bike).palette}

    assert list(palette) == ["frame", "fork", "wheel", "tire", "brake", "drivetrain", "chain", "pedal",
                             "saddle", "handlebar", "other"]
    assert "rim" not in palette and "spoke" not in palette
    assert [t.value for t in palette["tire"].targets] == [f"component:{wheel.id}"]
    assert [t.value for t in palette["pedal"].targets] == [f"bike:{bike.id}"]
    assert [t.value for t in palette["frame"].targets] == [f"bike:{bike.id}"]
    assert palette["frame"].label == "Frame"


# ------------------------------------------------ unified screen: any root (specs/005, M2)


def test_a_bike_screen_has_a_garage_breadcrumb_and_no_part(db_path):
    bike = bike_service.create_bike(name="Road")

    view = builder_service.build_view(f"bike:{bike.id}")

    assert view.crumbs == [("Garage", "/"), ("Road", None)]
    assert view.bike.id == bike.id and view.component is None and view.title == "Road"


def test_a_part_screen_is_scoped_to_its_own_sub_parts(db_path):
    bike = bike_service.create_bike(name="Road")
    front = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Front tire", "tire", parent_component_id=front.id)
    _mk("Rear tire", "tire", parent_component_id=rear.id)
    spare = _mk("Spare tire", "tire")

    view = builder_service.build_view(f"component:{front.id}")

    assert view.root_ref == f"component:{front.id}" and view.component.id == front.id
    assert [n.component.id for n in view.nodes] == [tire.id]
    assert view.root_accepts == ["other"]  # the single tire slot is taken
    assert [i.component.id for i in view.storage] == [spare.id]
    assert view.title == "Front wheel"


def test_part_screen_targets_stay_inside_the_part(db_path):
    bike = bike_service.create_bike(name="Road")
    front = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear wheel", "wheel", parent_bike_id=bike.id)
    spare = _mk("Spare tire", "tire")

    view = builder_service.build_view(f"component:{front.id}")

    targets = [t.value for t in view.storage[0].targets]
    assert targets == [f"component:{front.id}"]  # the rear wheel is another screen
    assert rear.id and spare.id
    palette = {p.type: p for p in view.palette}
    assert [t.value for t in palette["tire"].targets] == [f"component:{front.id}"]
    assert palette["frame"].targets == []  # frames mount on the bike, which is not in scope here
    assert [t.label for t in palette["tire"].targets] == ["Front wheel"]


def test_storage_part_screen_excludes_itself_from_the_storage_list(db_path):
    wheel = _mk("Spare wheel", "wheel")
    other = _mk("Spare saddle", "saddle")

    view = builder_service.build_view(f"component:{wheel.id}")

    assert view.crumbs == [("Garage", "/"), ("Storage", "/components"), ("Spare wheel", None)]
    assert [i.component.id for i in view.storage] == [other.id]


def test_breadcrumbs_walk_up_through_every_ancestor(db_path):
    bike = bike_service.create_bike(name="Road")
    drivetrain = _mk("Drivetrain", "drivetrain", parent_bike_id=bike.id)
    chain = _mk("Chain", "chain", parent_component_id=drivetrain.id)
    valve = _mk("Link", "other", parent_component_id=chain.id)

    crumbs = builder_service.breadcrumbs(f"component:{valve.id}")

    assert crumbs == [
        ("Garage", "/"), ("Road", f"/bikes/{bike.id}"), ("Drivetrain", f"/components/{drivetrain.id}"),
        ("Chain", f"/components/{chain.id}"), ("Link", None),
    ]


@pytest.mark.parametrize("bad", ["", "bike", "bike:", "bike:x", "wheel:1", "component:-1", "1;2"])
def test_malformed_roots_are_refused(db_path, bad):
    with pytest.raises(ValueError):
        builder_service.parse_root(bad)


def test_unknown_roots_have_no_view(db_path):
    assert builder_service.build_view("component:999") is None
    assert builder_service.build_view("bike:999") is None


def test_scope_ids_are_the_bike_tree_or_the_part_and_its_sub_parts(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    assert builder_service.scope_component_ids(f"bike:{bike.id}") == {wheel.id, tire.id, saddle.id}
    assert builder_service.scope_component_ids(f"component:{wheel.id}") == {wheel.id, tire.id}


def test_actions_are_limited_to_the_screens_scope(db_path):
    bike = bike_service.create_bike(name="Road")
    front = _mk("Front", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire")
    root = f"component:{front.id}"

    with pytest.raises(ValueError):  # destination is on the rear wheel, outside this screen
        builder_service.move_part(root, tire.id, {"parent_bike_id": None, "parent_component_id": rear.id})
    with pytest.raises(ValueError):  # adding onto the bike from a part screen
        builder_service.add_part(root, "wheel", {"parent_bike_id": bike.id, "parent_component_id": None})
    with pytest.raises(ValueError):  # deleting a part that is not in scope
        builder_service.delete_part(root, rear.id)
    with pytest.raises(ValueError):  # moving a mounted part that is not in scope
        builder_service.move_part(root, rear.id, {"parent_bike_id": None, "parent_component_id": None})

    builder_service.move_part(root, tire.id, {"parent_bike_id": None, "parent_component_id": front.id})
    assert component_service.get_component(tire.id).parent_component_id == front.id


def test_add_part_refuses_storage_as_a_destination(db_path):
    bike = bike_service.create_bike(name="Road")

    with pytest.raises(ValueError):
        builder_service.add_part(f"bike:{bike.id}", "frame", {"parent_bike_id": None, "parent_component_id": None})


def test_delete_part_needs_confirmation_for_sub_parts_and_then_deletes_the_sub_tree(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    root = f"bike:{bike.id}"

    with pytest.raises(component_service.ConfirmationRequiredError):
        builder_service.delete_part(root, wheel.id)
    assert component_service.get_component(wheel.id) is not None

    builder_service.delete_part(root, wheel.id, confirmed=True)

    assert component_service.get_component(wheel.id) is None and component_service.get_component(tire.id) is None


def test_delete_part_without_dependants_deletes_at_once(db_path):
    bike = bike_service.create_bike(name="Road")
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    builder_service.delete_part(f"bike:{bike.id}", saddle.id)

    assert component_service.get_component(saddle.id) is None


def test_the_part_can_delete_itself_from_its_own_screen(db_path):
    bike = bike_service.create_bike(name="Road")
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    builder_service.delete_part(f"component:{saddle.id}", saddle.id)

    assert component_service.get_component(saddle.id) is None
