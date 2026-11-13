"""Parts being added and removed are NOT logged in maintenance history (specs/022).

Installs and removals live in the Install History (installation periods); maintenance history is
only maintenance work. This file replaces the specs/006 M2 tests that asserted the old events.
"""

import pytest

from app.db import connection
from app.services import bike_service, component_service, maintenance_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _bike(name="Road Bike"):
    return bike_service.create_bike(name=name)


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def _logs(*entities):
    """Every maintenance entry on the given bikes and parts, as (description)."""
    found = []
    for entity in entities:
        lister = (
            maintenance_service.list_for_bike
            if isinstance(entity, bike_service.Bike)
            else maintenance_service.list_for_component
        )
        found += [e.description for e in lister(entity.id)]
    return found


def test_adding_a_part_to_a_bike_or_a_part_logs_nothing(db_path):
    bike = _bike()
    chain = _mk("Chain 1", "chain", parent_bike_id=bike.id)
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    assert _logs(bike, chain, wheel, tire) == []


def test_creating_in_storage_logs_nothing(db_path):
    assert _logs(_mk("Spare", "saddle")) == []


def test_moving_and_removing_parts_logs_nothing(db_path):
    bike = _bike()
    front = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=front.id)

    component_service.move_component(tire.id, parent_component_id=rear.id)
    component_service.move_component(tire.id)  # to storage
    component_service.move_component(tire.id, parent_bike_id=bike.id)

    assert _logs(bike, front, rear, tire) == []


def test_reordering_logs_nothing(db_path):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    a = _mk("A", "tube", parent_component_id=wheel.id)
    b = _mk("B", "tube", parent_component_id=wheel.id)

    component_service.move_component(b.id, parent_component_id=wheel.id, before_component_id=a.id)

    assert _logs(wheel) == []


def test_deleting_a_part_or_a_bike_logs_nothing(db_path):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    component_service.delete_component(wheel.id, confirmed=True)
    bike_service.delete_bike(bike.id, confirmed=True)

    assert _logs(tire, saddle) == []


def test_the_installation_periods_still_record_every_move(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    component_service.move_component(saddle.id)  # to storage

    with connection.get_connection() as conn:
        rows = conn.execute(
            "SELECT installed_at, removed_at FROM component_installation_period WHERE component_id = ?",
            (saddle.id,),
        ).fetchall()
    assert len(rows) == 1 and rows[0]["removed_at"] is not None


def test_a_part_with_nothing_logged_deletes_without_the_history_confirmation(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    component_service.delete_component(saddle.id)  # no confirmation needed

    assert component_service.get_component(saddle.id) is None


def test_real_maintenance_still_triggers_the_confirmation(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)
    maintenance_service.log_maintenance(component_id=saddle.id, description="Greased post", performed_at="2026-05-01")

    with pytest.raises(component_service.ConfirmationRequiredError):
        component_service.delete_component(saddle.id)
