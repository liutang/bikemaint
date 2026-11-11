import pytest

from app.db import connection
from app.services import component_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _create_bike(name="Test Bike"):
    from app.services import bike_service

    return bike_service.create_bike(name=name)


def test_create_component_in_storage_by_default(db_path):
    component = component_service.create_component(name="Spare Tire", component_type="tire")

    assert component.parent_bike_id is None
    assert component.parent_component_id is None
    assert component.total_mileage == 0


def test_second_single_instance_type_under_same_parent_is_rejected(db_path):
    bike = _create_bike()
    component_service.create_component(
        name="Frame", component_type="frame", parent_bike_id=bike.id
    )

    with pytest.raises(component_service.ComponentNestingConflictError):
        component_service.create_component(
            name="Second Frame", component_type="frame", parent_bike_id=bike.id
        )


def test_multi_instance_types_allow_more_than_one_under_the_same_parent(db_path):
    bike = _create_bike()
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike.id
    )

    spoke_a = component_service.create_component(
        name="Spoke A", component_type="spoke", parent_component_id=wheel.id
    )
    spoke_b = component_service.create_component(
        name="Spoke B", component_type="spoke", parent_component_id=wheel.id
    )

    assert spoke_a.id != spoke_b.id


def test_different_single_instance_types_coexist_under_the_same_parent(db_path):
    bike = _create_bike()
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike.id
    )

    hub = component_service.create_component(
        name="Hub", component_type="hub", parent_component_id=wheel.id
    )
    rim = component_service.create_component(
        name="Rim", component_type="rim", parent_component_id=wheel.id
    )

    assert hub.id != rim.id


def test_move_between_bikes_opens_and_closes_installation_periods(db_path):
    bike_a = _create_bike("Bike A")
    bike_b = _create_bike("Bike B")
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike_a.id
    )

    component_service.move_component(wheel.id, parent_bike_id=bike_b.id)

    with connection.get_connection() as conn:
        periods = conn.execute(
            "SELECT * FROM component_installation_period WHERE component_id = ? ORDER BY id",
            (wheel.id,),
        ).fetchall()

    assert len(periods) == 2
    assert periods[0]["parent_bike_id"] == bike_a.id
    assert periods[0]["removed_at"] is not None
    assert periods[1]["parent_bike_id"] == bike_b.id
    assert periods[1]["removed_at"] is None

    moved = component_service.get_component(wheel.id)
    assert moved.parent_bike_id == bike_b.id


def test_move_to_storage_closes_period_and_opens_none(db_path):
    bike = _create_bike()
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike.id
    )

    component_service.move_component(wheel.id, parent_bike_id=None, parent_component_id=None)

    with connection.get_connection() as conn:
        periods = conn.execute(
            "SELECT * FROM component_installation_period WHERE component_id = ?",
            (wheel.id,),
        ).fetchall()

    assert len(periods) == 1
    assert periods[0]["removed_at"] is not None

    moved = component_service.get_component(wheel.id)
    assert moved.parent_bike_id is None
    assert moved.parent_component_id is None


def test_move_preserves_own_mileage_and_history(db_path):
    bike_a = _create_bike("Bike A")
    bike_b = _create_bike("Bike B")
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike_a.id, manual_baseline_mileage=42.0
    )

    moved = component_service.move_component(wheel.id, parent_bike_id=bike_b.id)

    assert moved.total_mileage == 42.0
    assert moved.manual_baseline_mileage == 42.0


def test_move_rejects_destination_that_already_has_the_single_instance_type(db_path):
    bike = _create_bike()
    component_service.create_component(name="Frame", component_type="frame", parent_bike_id=bike.id)
    lone_frame = component_service.create_component(name="Lone Frame", component_type="frame")

    with pytest.raises(component_service.ComponentNestingConflictError):
        component_service.move_component(lone_frame.id, parent_bike_id=bike.id)


# ------------------------------------------------ placement rules (specs/004-bike-builder, M2)


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def test_create_refuses_a_part_on_a_parent_that_cannot_hold_it(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    with pytest.raises(component_service.ComponentPlacementError) as error:
        _mk("Pedal", "pedal", parent_component_id=wheel.id)

    assert str(error.value) == "A pedal can be mounted on a crankset, not on a wheel."
    assert component_service.get_tree_for_bike(bike.id) == [component_service.get_component(wheel.id)]


def test_placement_error_is_also_a_nesting_conflict_so_existing_handlers_catch_it(db_path):
    assert issubclass(
        component_service.ComponentPlacementError, component_service.ComponentNestingConflictError
    )


def test_create_accepts_valid_chains(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)
    tire = _mk("Tire", "tire", parent_component_id=rim.id)
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal", parent_component_id=crank.id)

    assert (tire.parent_component_id, pedal.parent_component_id) == (rim.id, crank.id)


def test_create_on_the_bike_directly_refuses_a_tire(db_path):
    bike = _create_bike()

    with pytest.raises(component_service.ComponentPlacementError, match="not on the bike"):
        _mk("Tire", "tire", parent_bike_id=bike.id)


def test_storage_accepts_every_type(db_path):
    for component_type in ("pedal", "tire", "frame", "cassette"):
        assert _mk(f"Spare {component_type}", component_type).parent_bike_id is None


def test_move_refuses_an_invalid_parent_and_keeps_the_component_where_it_was(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    with pytest.raises(component_service.ComponentPlacementError):
        component_service.move_component(pedal.id, parent_component_id=wheel.id)

    assert component_service.get_component(pedal.id).parent_component_id is None


def test_move_to_a_valid_parent_works_and_back_to_storage_always_works(db_path):
    bike = _create_bike()
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    moved = component_service.move_component(pedal.id, parent_component_id=crank.id)
    assert moved.parent_component_id == crank.id
    stored = component_service.move_component(pedal.id)
    assert (stored.parent_bike_id, stored.parent_component_id) == (None, None)


def test_changing_a_type_is_checked_against_the_current_parent(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    hub = _mk("Hub", "hub", parent_component_id=wheel.id)

    with pytest.raises(component_service.ComponentPlacementError):
        component_service.update_component(
            hub.id, name="Hub", component_type="saddle", manual_baseline_mileage=0
        )


def test_changing_a_type_is_refused_if_existing_children_would_no_longer_fit(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)
    _mk("Tire", "tire", parent_component_id=rim.id)

    with pytest.raises(component_service.ComponentPlacementError, match="tire"):
        component_service.update_component(
            rim.id, name="Rim", component_type="hub", manual_baseline_mileage=0
        )


def test_pre_existing_invalid_arrangements_stay_readable_and_editable(db_path):
    bike = _create_bike()
    # Simulates data from before the rules: a tire mounted straight on the bike.
    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at) "
            "VALUES ('Old tire', 'tire', ?, 'x', 'x')",
            (bike.id,),
        )
    tire = component_service.get_tree_for_bike(bike.id)[0]

    renamed = component_service.update_component(
        tire.id, name="Old tire renamed", component_type="tire", manual_baseline_mileage=5
    )

    assert renamed.name == "Old tire renamed"


def test_move_targets_list_only_valid_places(db_path):
    bike = _create_bike("Road Bike")
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")
    tire = _mk("Tire", "tire")

    pedal_targets = {t.value for t in component_service.list_move_targets(pedal.id)}
    tire_targets = {t.value for t in component_service.list_move_targets(tire.id)}

    assert pedal_targets == {f"component:{crank.id}"}  # storage is where it already is
    assert tire_targets == {f"component:{rim.id}"}
    assert f"component:{wheel.id}" not in pedal_targets and f"bike:{bike.id}" not in tire_targets


def test_move_targets_include_storage_for_mounted_parts_and_skip_the_current_parent(db_path):
    bike = _create_bike()
    crank = _mk("Crankset", "crankset", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal", parent_component_id=crank.id)

    values = [t.value for t in component_service.list_move_targets(pedal.id)]

    assert values == ["storage"]


def test_move_targets_exclude_self_descendants_and_full_single_slots(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel A", "wheel", parent_bike_id=bike.id)
    other_wheel_bike = _create_bike("Other")
    wheel_b = _mk("Wheel B", "wheel", parent_bike_id=other_wheel_bike.id)
    hub = _mk("Hub", "hub", parent_component_id=wheel.id)

    # hub could go on wheel B, but not back on its own parent; wheel B already has no hub.
    assert [t.value for t in component_service.list_move_targets(hub.id)] == [
        f"component:{wheel_b.id}", "storage",
    ]
    _mk("Hub B", "hub", parent_component_id=wheel_b.id)
    # now wheel B's single hub slot is taken, so it is no longer offered
    assert [t.value for t in component_service.list_move_targets(hub.id)] == ["storage"]
    # a wheel is never offered its own sub-tree (not a valid kind anyway) and never itself
    assert all(t.value != f"component:{wheel.id}" for t in component_service.list_move_targets(wheel.id))


def test_move_target_labels_show_the_path(db_path):
    bike = _create_bike("Road Bike")
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rim = _mk("Rim", "rim", parent_component_id=wheel.id)
    tire = _mk("Tire", "tire")

    labels = {t.value: t.label for t in component_service.list_move_targets(tire.id)}

    assert labels[f"component:{rim.id}"] == "Road Bike › Front wheel › Rim"


def test_move_targets_for_an_unknown_component_raise(db_path):
    with pytest.raises(LookupError):
        component_service.list_move_targets(999)
