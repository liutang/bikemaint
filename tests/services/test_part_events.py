"""Parts being added and removed are logged in the maintenance history (specs/006, M2)."""

import re
from datetime import datetime, timezone

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


def _bike_log(bike):
    return [(e.kind, e.description) for e in maintenance_service.list_for_bike(bike.id)]


def _part_log(part):
    return [(e.kind, e.description) for e in maintenance_service.list_for_component(part.id)]


def test_adding_a_chain_to_a_bike_is_logged_on_the_bike_and_the_chain(db_path):
    bike = _bike()

    chain = _mk("Chain 1", "chain", parent_bike_id=bike.id)

    assert _bike_log(bike) == [("event", "Added Chain 1 (chain)")]
    assert _part_log(chain) == [("event", "Installed on Road Bike")]


def test_adding_to_a_part_logs_on_that_part(db_path):
    bike = _bike()
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)

    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    assert ("event", "Added Tire (tire)") in _part_log(wheel)
    assert _part_log(tire) == [("event", "Installed on Front wheel")]


def test_creating_in_storage_logs_nothing(db_path):
    spare = _mk("Spare", "saddle")

    assert _part_log(spare) == []


def test_taking_a_tire_off_a_wheel_logs_the_removal_on_the_wheel_and_the_tire(db_path):
    bike = _bike()
    wheel = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    component_service.move_component(tire.id)  # to storage

    assert _part_log(wheel)[-1] == ("event", "Removed Tire (tire)")
    assert _part_log(tire)[-1] == ("event", "Removed from Front wheel")


def test_moving_between_parents_logs_removal_then_addition(db_path):
    bike = _bike()
    front = _mk("Front wheel", "wheel", parent_bike_id=bike.id)
    rear = _mk("Rear wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=front.id)

    component_service.move_component(tire.id, parent_component_id=rear.id)

    assert _part_log(front)[-1] == ("event", "Removed Tire (tire)")
    assert _part_log(rear)[-1] == ("event", "Added Tire (tire)")
    assert _part_log(tire)[-2:] == [("event", "Removed from Front wheel"), ("event", "Installed on Rear wheel")]


def test_mounting_a_stored_part_logs_only_the_addition(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle")

    component_service.move_component(saddle.id, parent_bike_id=bike.id)

    assert _bike_log(bike) == [("event", "Added Saddle (saddle)")]
    assert _part_log(saddle) == [("event", "Installed on Road Bike")]


def test_reordering_logs_nothing(db_path):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    a = _mk("A", "other", parent_component_id=wheel.id)
    b = _mk("B", "other", parent_component_id=wheel.id)
    before = len(maintenance_service.list_for_component(wheel.id))

    component_service.move_component(b.id, parent_component_id=wheel.id, before_component_id=a.id)

    assert len(maintenance_service.list_for_component(wheel.id)) == before


def test_moving_a_part_with_sub_parts_logs_only_the_part_itself(db_path):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)
    tire_log = _part_log(tire)

    component_service.move_component(wheel.id)

    assert _part_log(tire) == tire_log  # the tire stayed on the wheel, so nothing happened to it
    assert _bike_log(bike)[-1] == ("event", "Removed Wheel (wheel)")


def test_deleting_a_part_logs_the_removal_and_the_sub_parts_leaving(db_path):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)
    tire = _mk("Tire", "tire", parent_component_id=wheel.id)

    component_service.delete_component(wheel.id, confirmed=True)

    assert _bike_log(bike)[-1] == ("event", "Removed Wheel (wheel)")
    assert _part_log(tire)[-1] == ("event", "Removed from Wheel (deleted)")


def test_deleting_a_bike_logs_its_parts_leaving(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)

    bike_service.delete_bike(bike.id, confirmed=True)

    assert _part_log(saddle)[-1] == ("event", "Removed from Road Bike (deleted)")


def test_events_record_the_mileage_and_a_utc_timestamp(db_path):
    bike = bike_service.create_bike(name="Road Bike", manual_baseline_mileage=120.5)

    _mk("Chain", "chain", parent_bike_id=bike.id)

    (entry,) = maintenance_service.list_for_bike(bike.id)
    assert entry.mileage_at_service == 120.5
    assert entry.performed_at == datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z", entry.created_at)
    assert entry.kind == "event" and entry.schedule_id is None


def test_events_do_not_trigger_the_maintenance_history_confirmation(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)  # logs an event on the saddle

    component_service.delete_component(saddle.id)  # no confirmation needed: only an event exists

    assert component_service.get_component(saddle.id) is None


def test_real_maintenance_still_triggers_the_confirmation(db_path):
    bike = _bike()
    saddle = _mk("Saddle", "saddle", parent_bike_id=bike.id)
    maintenance_service.log_maintenance(component_id=saddle.id, description="Greased post", performed_at="2026-05-01")

    with pytest.raises(component_service.ConfirmationRequiredError):
        component_service.delete_component(saddle.id)
