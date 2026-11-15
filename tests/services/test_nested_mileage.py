"""A part earns its parents' miles (specs/064-nested-part-mileage)."""

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_history_service as history, component_service

D = "T00:00:00.000000Z"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _ride(bike, n, miles, when):
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles, occurred_at=when + "T12:00:00.000000Z")


def _miles(c):
    return component_service.get_component(c.id).total_mileage


def _setup():
    bike = bike_service.create_bike(name="Madone")
    wheels = component_service.create_component(name="Wheelset", component_type="wheel")
    tire = component_service.create_component(name="Tire", component_type="tire")
    return bike, wheels, tire


def test_a_tire_inside_a_wheelset_earns_the_wheelsets_bike_time(db_path):
    bike, wheels, tire = _setup()
    _ride(bike, 1, 10, "2021-01-01")   # wheelset only
    _ride(bike, 2, 20, "2022-08-01")   # both
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2020-10-08" + D, removed_at="2023-01-23" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-06-22" + D, removed_at="2023-01-23" + D)

    assert _miles(wheels) == 30 and _miles(tire) == 20


def test_only_the_overlap_counts_and_storage_time_counts_nothing(db_path):
    bike, wheels, tire = _setup()
    _ride(bike, 1, 5, "2022-07-01")    # tire in wheelset, wheelset in storage
    _ride(bike, 2, 7, "2022-09-01")    # overlap
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-08-01" + D, removed_at="2022-10-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-06-01" + D, removed_at="2022-12-01" + D)

    assert _miles(tire) == 7


def test_deep_nesting_and_each_ride_counted_once(db_path):
    bike, wheels, tire = _setup()
    rim = component_service.create_component(name="Rim", component_type="rim")
    _ride(bike, 1, 10, "2022-03-01")
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2022-12-01" + D)
    history.log_period(rim.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-01-01" + D, removed_at="2022-12-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=rim.id, installed_at="2022-02-01" + D, removed_at="2022-06-01" + D)
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-06-01" + D, removed_at="2022-07-01" + D)

    assert _miles(tire) == 10


def test_the_bike_field_is_ignored_when_inside_a_part(db_path):
    bike, wheels, tire = _setup()
    other = bike_service.create_bike(name="Other")
    _ride(other, 1, 99, "2022-08-01")
    _ride(bike, 2, 20, "2022-08-01")
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2023-01-01" + D)
    period = history.log_period(tire.id, bike_id=other.id, parent_component_id=wheels.id, installed_at="2022-06-01" + D, removed_at="2023-01-01" + D)

    assert period.parent_bike_id is None and _miles(tire) == 20


def test_period_rows_and_ride_lists_use_the_same_rides(db_path):
    bike, wheels, tire = _setup()
    _ride(bike, 2, 20, "2022-08-01")
    history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2023-01-01" + D)
    period = history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-06-01" + D, removed_at="2023-01-01" + D)

    (row,) = history.describe_history(tire.id)
    with connection.get_connection() as conn:
        rides = mileage_db.list_rides_for_period(conn, period)
    assert row["miles"] == 20 and [r.distance_miles for r in rides] == [20]


def test_changing_the_parents_periods_recomputes_the_parts_inside(db_path):
    bike, wheels, tire = _setup()
    _ride(bike, 2, 20, "2022-08-01")
    history.log_period(tire.id, bike_id=bike.id, parent_component_id=wheels.id, installed_at="2022-06-01" + D, removed_at="2023-01-01" + D)
    assert _miles(tire) == 0

    parent = history.log_period(wheels.id, bike_id=bike.id, installed_at="2022-01-01" + D, removed_at="2023-01-01" + D)
    assert _miles(tire) == 20

    history.delete_period(parent.id)
    assert _miles(tire) == 0
