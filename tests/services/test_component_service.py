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
        name="Rim", component_type="rim", parent_bike_id=bike.id
    )

    with pytest.raises(component_service.ComponentNestingConflictError):
        component_service.create_component(
            name="Second Rim", component_type="rim", parent_bike_id=bike.id
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
    component_service.create_component(name="Rim", component_type="rim", parent_bike_id=bike.id)
    lone_rim = component_service.create_component(name="Lone Rim", component_type="rim")

    with pytest.raises(component_service.ComponentNestingConflictError):
        component_service.move_component(lone_rim.id, parent_bike_id=bike.id)
