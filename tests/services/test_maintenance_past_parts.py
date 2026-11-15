"""Maintenance history includes parts attached at the time (specs/066-maintenance-past-parts)."""

import pytest

from app.db import connection
from app.services import bike_service, component_history_service as history, component_service, maintenance_service

D = "T00:00:00.000000Z"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _log(**kw):
    return maintenance_service.log_maintenance(description="Clean", mileage_at_service=0, **kw)


def _names(rows):
    return sorted((r.part_name, r.entry.performed_at) for r in rows)


def test_a_removed_part_shows_entries_made_while_it_was_on_the_bike(db_path):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain")
    history.log_period(chain.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2022-06-01" + D)
    _log(component_id=chain.id, performed_at="2022-03-01")   # while on
    _log(component_id=chain.id, performed_at="2022-08-01")   # after removal

    rows = maintenance_service.list_for_bike_rows(bike.id)

    assert _names(rows) == [("Chain", "2022-03-01")] and not rows[0].is_own


def test_parts_inside_a_past_part_count_and_each_entry_appears_once(db_path):
    bike = bike_service.create_bike(name="Road")
    wheels = component_service.create_component(name="Wheelset", component_type="wheel")
    tire = component_service.create_component(name="Tire", component_type="tire")
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2022-12-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-02-01" + D, removed_at="2022-05-01" + D)
    _log(component_id=tire.id, performed_at="2022-03-01")
    _log(component_id=tire.id, performed_at="2022-07-01")   # tire out of the wheelset by then

    assert _names(maintenance_service.list_for_bike_rows(bike.id)) == [("Tire", "2022-03-01")]


def test_a_part_lists_entries_of_parts_that_were_inside_it(db_path):
    bike = bike_service.create_bike(name="Road")
    wheels = component_service.create_component(name="Wheelset", component_type="wheel")
    rim = component_service.create_component(name="Rim", component_type="rim")
    tire = component_service.create_component(name="Tire", component_type="tire")
    history.log_period(rim.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-01-01" + D, removed_at="2022-12-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=rim.id, installed_at="2022-02-01" + D, removed_at="2022-05-01" + D)
    _log(component_id=tire.id, performed_at="2022-03-01")
    _log(component_id=tire.id, performed_at="2022-09-01")
    _log(component_id=rim.id, performed_at="2022-04-01")
    _log(component_id=wheels.id, performed_at="2022-04-02")

    rows = maintenance_service.list_for_component_tree(wheels.id)

    assert _names(rows) == [("Rim", "2022-04-01"), ("Tire", "2022-03-01"), ("Wheelset", "2022-04-02")]
    assert [r.is_own for r in rows if r.part_name == "Wheelset"] == [True]


def test_currently_attached_parts_are_not_duplicated(db_path):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    _log(component_id=chain.id, performed_at="2022-03-01")

    assert len(maintenance_service.list_for_bike_rows(bike.id)) == 1


def test_a_deleted_part_is_named_without_a_link(db_path, signed_in_client=None):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain")
    history.log_period(chain.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2022-06-01" + D)
    _log(component_id=chain.id, performed_at="2022-03-01")
    component_service.delete_component(chain.id, confirmed=True, keep_history=True)

    (row,) = maintenance_service.list_for_bike_rows(bike.id)

    assert row.part_name == "Chain" and row.part_deleted
