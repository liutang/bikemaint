"""Any part on any part, any number of times (specs/020-free-placement-and-categories, US1)."""

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


def test_any_kind_can_be_created_under_any_kind(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    pedal_on_wheel = _mk("Pedal", "pedal", parent_component_id=wheel.id)
    saddle_on_tire = _mk("Saddle", "saddle", parent_component_id=tire.id)
    tire_on_bike = _mk("Spare tire", "tire", parent_bike_id=bike.id)
    lights_on_chain = _mk("Lights", "lights", parent_component_id=_mk("Chain", "chain", parent_bike_id=bike.id).id)

    assert pedal_on_wheel.parent_component_id == wheel.id
    assert saddle_on_tire.parent_component_id == tire.id
    assert tire_on_bike.parent_bike_id == bike.id
    assert lights_on_chain.parent_component_id is not None


def test_a_parent_can_hold_any_number_of_the_same_kind(db_path):
    bike = bike_service.create_bike(name="Road")
    for index in range(3):
        _mk(f"Chain {index}", "chain", parent_bike_id=bike.id)
        _mk(f"Frame {index}", "frame", parent_bike_id=bike.id)

    assert len(component_service.get_tree_for_bike(bike.id)) == 6


def test_a_part_can_be_moved_onto_any_other_part_or_the_bike(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    moved = component_service.move_component(pedal.id, parent_component_id=wheel.id)
    assert moved.parent_component_id == wheel.id
    moved = component_service.move_component(pedal.id, parent_bike_id=bike.id)
    assert moved.parent_bike_id == bike.id


def test_a_part_still_cannot_go_inside_itself_or_its_own_sub_tree(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    with pytest.raises(ValueError, match="itself"):
        component_service.move_component(wheel.id, parent_component_id=wheel.id)
    with pytest.raises(ValueError, match="sub-tree"):
        component_service.move_component(wheel.id, parent_component_id=tire.id)


def test_changing_a_type_is_allowed_whatever_it_holds(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Pedal", "pedal", parent_component_id=wheel.id)

    updated = component_service.update_component(
        wheel.id, name="Wheel", component_type="saddle", manual_baseline_mileage=0
    )

    assert updated.component_type == "saddle"


def test_every_slot_in_scope_is_a_target_for_a_new_part(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    everything = {f"bike:{bike.id}", f"component:{wheel.id}", f"component:{tire.id}"}

    values = {t.value for t in component_service.list_placement_targets(bike_id=bike.id)}
    assert values == everything


def test_move_targets_are_every_slot_except_the_part_its_sub_tree_and_where_it_is(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    from_saddle = {t.value for t in component_service.list_move_targets(saddle.id)}
    from_wheel = {t.value for t in component_service.list_move_targets(wheel.id)}

    assert from_saddle == {f"component:{wheel.id}", f"component:{tire.id}", "storage"}
    # the bike is where it is, and its own sub-tree (the tire) is excluded
    assert from_wheel == {f"component:{saddle.id}", "storage"}


def test_the_builder_has_no_per_kind_accept_lists_any_more(db_path):
    bike = bike_service.create_bike(name="Road")
    _mk("Wheel", "wheel", parent_bike_id=bike.id)

    view = builder_service.build_view(bike.id)

    assert not hasattr(view, "root_accepts")
    assert not hasattr(view.nodes[0], "accepts")


def test_a_missing_parent_is_refused_cleanly_for_create_and_move(db_path):
    bike = bike_service.create_bike(name="Road")
    pedal = _mk("Pedal", "pedal", parent_bike_id=bike.id)

    with pytest.raises(LookupError):
        _mk("Chain", "chain", parent_component_id=999)
    with pytest.raises(LookupError):
        component_service.move_component(pedal.id, parent_component_id=999)
    with pytest.raises(LookupError):
        component_service.move_component(pedal.id, parent_bike_id=999)
    assert component_service.get_component(pedal.id).parent_bike_id == bike.id
