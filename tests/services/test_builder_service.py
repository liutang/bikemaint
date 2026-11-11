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
