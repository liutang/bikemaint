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


def test_a_second_part_of_the_same_kind_under_one_parent_is_allowed(db_path):
    bike = _create_bike()
    component_service.create_component(name="Frame", component_type="frame", parent_bike_id=bike.id)

    second = component_service.create_component(
        name="Second Frame", component_type="frame", parent_bike_id=bike.id
    )

    assert second.parent_bike_id == bike.id


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


def test_move_onto_a_parent_that_already_has_the_kind_is_allowed(db_path):
    bike = _create_bike()
    component_service.create_component(name="Frame", component_type="frame", parent_bike_id=bike.id)
    lone_frame = component_service.create_component(name="Lone Frame", component_type="frame")

    moved = component_service.move_component(lone_frame.id, parent_bike_id=bike.id)

    assert moved.parent_bike_id == bike.id


# ------------------------------------------------ placement rules (specs/004-bike-builder, M2)


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def test_create_allows_a_part_on_any_parent(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    pedal = _mk("Pedal", "pedal", parent_component_id=wheel.id)

    assert pedal.parent_component_id == wheel.id


def test_create_accepts_valid_chains(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    drivetrain = _mk("Drivetrain", "drivetrain", parent_bike_id=bike.id)
    chain = _mk("Chain", "chain", parent_component_id=drivetrain.id)
    pedal = _mk("Pedal", "pedal", parent_bike_id=bike.id)

    assert (tire.parent_component_id, chain.parent_component_id) == (wheel.id, drivetrain.id)
    assert pedal.parent_bike_id == bike.id


def test_create_on_the_bike_directly_allows_a_tire(db_path):
    bike = _create_bike()

    assert _mk("Tire", "tire", parent_bike_id=bike.id).parent_bike_id == bike.id


def test_storage_accepts_every_type(db_path):
    for component_type in ("pedal", "tire", "frame", "cassette", "rim"):
        assert _mk(f"Spare {component_type}", component_type).parent_bike_id is None


def test_move_onto_any_parent_works(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")

    moved = component_service.move_component(pedal.id, parent_component_id=wheel.id)

    assert moved.parent_component_id == wheel.id


def test_move_to_a_valid_parent_works_and_back_to_storage_always_works(db_path):
    bike = _create_bike()
    pedal = _mk("Pedal", "pedal")

    moved = component_service.move_component(pedal.id, parent_bike_id=bike.id)
    assert moved.parent_bike_id == bike.id
    stored = component_service.move_component(pedal.id)
    assert (stored.parent_bike_id, stored.parent_component_id) == (None, None)


def test_changing_a_type_is_not_checked_against_the_current_parent(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    hub = _mk("Hub", "hub", parent_component_id=wheel.id)

    updated = component_service.update_component(
        hub.id, name="Hub", component_type="saddle", manual_baseline_mileage=0
    )

    assert updated.component_type == "saddle"


def test_changing_a_type_with_children_is_allowed(db_path):
    bike = _create_bike()
    drivetrain = _mk("Drivetrain", "drivetrain", parent_bike_id=bike.id)
    _mk("Chain", "chain", parent_component_id=drivetrain.id)

    updated = component_service.update_component(
        drivetrain.id, name="Drivetrain", component_type="saddle", manual_baseline_mileage=0
    )

    assert updated.component_type == "saddle"


def test_changing_a_type_to_an_older_finer_kind_is_refused(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    with pytest.raises(component_service.ComponentPlacementError, match="not an available"):
        component_service.update_component(
            wheel.id, name="Wheel", component_type="rim", manual_baseline_mileage=0
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


def test_move_targets_list_every_other_place(db_path):
    bike = _create_bike("Road Bike")
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    pedal = _mk("Pedal", "pedal")
    tire = _mk("Tire", "tire")

    pedal_targets = {t.value for t in component_service.list_move_targets(pedal.id)}
    tire_targets = {t.value for t in component_service.list_move_targets(tire.id)}

    everywhere = {f"bike:{bike.id}", f"component:{wheel.id}"}  # storage is where both already are
    assert pedal_targets == everywhere and tire_targets == everywhere


def test_move_targets_include_storage_for_mounted_parts_and_skip_the_current_parent(db_path):
    bike = _create_bike()
    pedal = _mk("Pedal", "pedal", parent_bike_id=bike.id)

    values = [t.value for t in component_service.list_move_targets(pedal.id)]

    assert values == ["storage"]


def test_move_targets_exclude_self_and_descendants_only(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel A", "wheel", parent_bike_id=bike.id)
    other_bike = _create_bike("Other")
    wheel_b = _mk("Wheel B", "wheel", parent_bike_id=other_bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    # the tire can go on the other bike, wheel B or storage, but not back on its own parent
    assert {t.value for t in component_service.list_move_targets(tire.id)} == {
        f"bike:{bike.id}", f"bike:{other_bike.id}", f"component:{wheel_b.id}", "storage",
    }
    _mk("Tire B", "tire", parent_component_id=wheel_b.id)
    # a part already on wheel B is no reason to hide wheel B
    assert f"component:{wheel_b.id}" in {t.value for t in component_service.list_move_targets(tire.id)}
    # a wheel is never offered itself or its own sub-tree
    assert all(t.value != f"component:{wheel.id}" for t in component_service.list_move_targets(wheel.id))
    assert all(t.value != f"component:{tire.id}" for t in component_service.list_move_targets(wheel.id))


def test_move_target_labels_show_the_path(db_path):
    bike = _create_bike("Road Bike")
    drivetrain = _mk("Drivetrain", "drivetrain", parent_bike_id=bike.id)
    chain = _mk("Chain", "chain")

    labels = {t.value: t.label for t in component_service.list_move_targets(chain.id)}

    assert labels[f"component:{drivetrain.id}"] == "Road Bike › Drivetrain"
    assert labels[f"bike:{bike.id}"] == "Road Bike"


def test_move_targets_for_an_unknown_component_raise(db_path):
    with pytest.raises(LookupError):
        component_service.list_move_targets(999)


# ------------------------------------------------ ordering and mounting (M3)


def _order(parent_bike_id=None, parent_component_id=None):
    return [
        c.name
        for c in (
            component_service.get_tree_for_bike(parent_bike_id)
            if parent_bike_id
            else component_service.get_descendants(parent_component_id)
        )
        if (c.parent_bike_id == parent_bike_id if parent_bike_id else c.parent_component_id == parent_component_id)
    ]


def test_reorder_within_the_same_parent_keeps_installation_history(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1, s2, s3 = (_mk(n, "spoke", parent_component_id=wheel.id) for n in ("S1", "S2", "S3"))
    with connection.get_connection() as conn:
        periods_before = conn.execute(
            "SELECT COUNT(*) AS c FROM component_installation_period WHERE component_id = ?", (s3.id,)
        ).fetchone()["c"]

    component_service.move_component(
        s3.id, parent_component_id=wheel.id, before_component_id=s1.id
    )

    assert _order(parent_component_id=wheel.id) == ["S3", "S1", "S2"]
    with connection.get_connection() as conn:
        periods_after = conn.execute(
            "SELECT COUNT(*) AS c FROM component_installation_period WHERE component_id = ?", (s3.id,)
        ).fetchone()["c"]
        open_periods = conn.execute(
            "SELECT COUNT(*) AS c FROM component_installation_period "
            "WHERE component_id = ? AND removed_at IS NULL", (s3.id,)
        ).fetchone()["c"]
    assert periods_after == periods_before and open_periods == 1


def test_reorder_to_the_end_with_no_before_target(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    s1, s2 = (_mk(n, "spoke", parent_component_id=wheel.id) for n in ("S1", "S2"))

    component_service.move_component(s1.id, parent_component_id=wheel.id)

    assert _order(parent_component_id=wheel.id) == ["S2", "S1"]


def test_move_to_another_parent_can_insert_before_a_sibling(db_path):
    bike = _create_bike()
    w1 = _mk("W1", "wheel", parent_bike_id=bike.id)
    other = _create_bike("Other")
    w2 = _mk("W2", "wheel", parent_bike_id=other.id)
    a, b = (_mk(n, "spoke", parent_component_id=w1.id) for n in ("A", "B"))
    c = _mk("C", "spoke", parent_component_id=w2.id)

    component_service.move_component(c.id, parent_component_id=w1.id, before_component_id=a.id)

    assert _order(parent_component_id=w1.id) == ["C", "A", "B"]


def test_before_target_must_be_a_sibling_under_the_destination(db_path):
    bike = _create_bike()
    w1 = _mk("W1", "wheel", parent_bike_id=bike.id)
    s = _mk("S", "spoke", parent_component_id=w1.id)
    stray = _mk("Stray", "spoke")

    with pytest.raises(ValueError):
        component_service.move_component(stray.id, parent_component_id=w1.id, before_component_id=999)
    assert component_service.get_component(stray.id).parent_component_id is None  # nothing moved


def test_moving_onto_the_current_parent_does_not_revalidate_legacy_arrangements(db_path):
    bike = _create_bike()
    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at)"
            " VALUES ('Old tire', 'tire', ?, 'x', 'x')", (bike.id,),
        )
        conn.execute(
            "INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at)"
            " VALUES ('Old tire 2', 'tire', ?, 'x', 'x')", (bike.id,),
        )
    first = component_service.get_tree_for_bike(bike.id)[0]

    component_service.move_component(first.id, parent_bike_id=bike.id)  # reorder to end only

    assert [c.name for c in component_service.get_tree_for_bike(bike.id)] == ["Old tire 2", "Old tire"]


def test_mount_new_component_uses_the_kind_name_and_allows_any_place(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    tire = component_service.mount_new_component("tire", parent_component_id=wheel.id)
    on_bike = component_service.mount_new_component("tire", parent_bike_id=bike.id)
    cable = component_service.mount_new_component("brake_cable", parent_bike_id=bike.id)

    assert (tire.name, tire.component_type, tire.parent_component_id) == ("Tire", "tire", wheel.id)
    assert on_bike.parent_bike_id == bike.id
    assert cable.name == "Brake Cable"


def test_mount_new_component_refuses_the_older_finer_kinds(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    with pytest.raises(component_service.ComponentPlacementError, match="not an available"):
        component_service.mount_new_component("rim", parent_component_id=wheel.id)


def test_mount_new_component_can_insert_before_a_sibling(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    first = _mk("Valve", "tube", parent_component_id=wheel.id)

    added = component_service.mount_new_component(
        "tube", parent_component_id=wheel.id, before_component_id=first.id
    )

    assert _order(parent_component_id=wheel.id) == [added.name, "Valve"]


def test_placement_targets_list_every_place_on_one_bike_only(db_path):
    bike = _create_bike("Road")
    other = _create_bike("Other")
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Wheel", "wheel", parent_bike_id=other.id)
    frame = _mk("Frame", "frame", parent_bike_id=bike.id)

    values = {t.value for t in component_service.list_placement_targets(bike_id=bike.id)}
    assert values == {f"bike:{bike.id}", f"component:{wheel.id}", f"component:{frame.id}"}


def test_move_targets_can_be_limited_to_one_bike(db_path):
    bike = _create_bike("Road")
    other = _create_bike("Other")
    wa = _mk("Wheel A", "wheel", parent_bike_id=bike.id)
    wb = _mk("Wheel B", "wheel", parent_bike_id=other.id)
    tire = _mk("Tire", "tire")

    limited = {t.value for t in component_service.list_move_targets(tire.id, only_bike_id=bike.id)}

    assert limited == {f"bike:{bike.id}", f"component:{wa.id}"}
    assert {t.value for t in component_service.list_move_targets(tire.id)} == {
        f"bike:{bike.id}", f"bike:{other.id}", f"component:{wa.id}", f"component:{wb.id}",
    }


# ------------------------------------------------ deleting keeps sub-parts (specs/006, M1)


def test_deleting_a_part_moves_its_sub_parts_to_storage(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    valve = _mk("Valve", "other", parent_component_id=tire.id)

    component_service.delete_component(wheel.id, confirmed=True)

    assert component_service.get_component(wheel.id) is None
    stored = component_service.get_component(tire.id)
    assert (stored.parent_bike_id, stored.parent_component_id) == (None, None)
    assert component_service.get_component(valve.id).parent_component_id == tire.id
    assert {c.id for c in component_service.list_in_storage()} == {tire.id}
    assert component_service.get_tree_for_bike(bike.id) == []


def test_deleting_a_part_closes_the_sub_parts_installation_periods(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    component_service.delete_component(wheel.id, confirmed=True)

    with connection.get_connection() as conn:
        open_on_bike = conn.execute(
            "SELECT COUNT(*) AS c FROM component_installation_period "
            "WHERE component_id = ? AND removed_at IS NULL AND parent_bike_id = ?",
            (tire.id, bike.id),
        ).fetchone()["c"]
    assert open_on_bike == 0  # it no longer accrues the bike's rides


def test_deleting_a_part_with_sub_parts_asks_first_and_says_they_move_to_storage(db_path):
    bike = _create_bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    _mk("Tire", "tire", parent_component_id=wheel.id)

    with pytest.raises(component_service.ConfirmationRequiredError, match="storage"):
        component_service.delete_component(wheel.id)
    assert component_service.get_component(wheel.id) is not None


def test_a_sub_parts_own_history_does_not_force_confirmation_of_the_parent(db_path):
    from app.services import maintenance_service

    bike = _create_bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)
    other = _mk("Bag", "other", parent_component_id=saddle.id)
    maintenance_service.log_maintenance(component_id=other.id, description="Checked", performed_at="2026-05-01")

    with pytest.raises(component_service.ConfirmationRequiredError):  # because it has a sub-part
        component_service.delete_component(saddle.id)
    component_service.delete_component(saddle.id, confirmed=True)

    assert component_service.get_component(other.id) is not None  # kept, with its history


# ------------------------------------------------ specs/022 US4: choosing a part


def test_list_all_parts_returns_active_parts_by_name(db_path):
    bike = _create_bike()
    _mk("Zed", "saddle", parent_bike_id=bike.id)
    _mk("Alpha", "chain")
    gone = _mk("Gone", "saddle")
    component_service.delete_component(gone.id)

    assert [c.name for c in component_service.list_all_parts()] == ["Alpha", "Zed"]
