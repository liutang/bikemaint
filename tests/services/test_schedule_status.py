from datetime import date, timedelta

import pytest

from app.services.schedule_service import Projection, due_status

TODAY = date(2026, 6, 15)


def _projection(due_at, *, overdue=False):
    return Projection(due_at=due_at, remaining_miles=None, is_low_confidence=False, is_overdue=overdue)


def test_overdue_projection_is_overdue_regardless_of_date():
    assert due_status(_projection(TODAY - timedelta(days=3), overdue=True), 7, TODAY) == "overdue"
    assert due_status(_projection(TODAY, overdue=True), 7, TODAY) == "overdue"


@pytest.mark.parametrize("days_out", [0, 1, 6, 7])
def test_due_within_the_lead_time_window_is_due_soon(days_out):
    assert due_status(_projection(TODAY + timedelta(days=days_out)), 7, TODAY) == "due_soon"


def test_due_one_day_past_the_window_is_on_track():
    assert due_status(_projection(TODAY + timedelta(days=8)), 7, TODAY) == "on_track"


def test_far_off_projection_is_on_track():
    assert due_status(_projection(TODAY + timedelta(days=200)), 7, TODAY) == "on_track"


def test_no_projected_date_means_no_estimate():
    assert due_status(_projection(None), 7, TODAY) == "no_estimate"


def test_zero_day_lead_time_only_flags_items_due_today():
    assert due_status(_projection(TODAY), 0, TODAY) == "due_soon"
    assert due_status(_projection(TODAY + timedelta(days=1)), 0, TODAY) == "on_track"


def test_overview_items_carry_a_status(tmp_path, monkeypatch):
    from app.db import connection
    from app.services import bike_service, schedule_service

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    bike = bike_service.create_bike(name="Road Bike")
    schedule_service.create_schedule(
        bike_id=bike.id, name="Soon", interval_days=3, today=date.today()
    )
    schedule_service.create_schedule(
        bike_id=bike.id, name="Later", interval_days=100, today=date.today()
    )

    items = {i.schedule.name: i.status for i in schedule_service.list_due_overview(lead_time_days=7)}

    assert items == {"Soon": "due_soon", "Later": "on_track"}


# ------------------------------------------------ which bike a schedule's part belongs to (specs/006, M1)

from app.db import connection  # noqa: E402
from app.services import bike_service, component_service, schedule_service  # noqa: E402


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def test_a_part_schedule_names_the_bike_the_part_is_on(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    bike = bike_service.create_bike(name="Gravel Bike")
    chain = component_service.create_component(name="Chain 1", component_type="chain", parent_bike_id=bike.id)
    schedule_service.create_schedule(component_id=chain.id, name="Re-wax", interval_days=30)

    (item,) = schedule_service.list_due_overview()

    assert (item.owner_name, item.bike_name) == ("Chain 1", "Gravel Bike")


def test_a_nested_part_names_the_bike_at_the_top_of_its_chain(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    bike = bike_service.create_bike(name="Road Bike")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    schedule_service.create_schedule(component_id=tire.id, name="Check pressure", interval_days=7)

    (item,) = schedule_service.list_due_overview()

    assert item.bike_name == "Road Bike"


def test_a_bike_level_schedule_has_no_bike_prefix(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    bike = bike_service.create_bike(name="Road Bike")
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=365)

    (item,) = schedule_service.list_due_overview()

    assert (item.owner_name, item.bike_name) == ("Road Bike", None)


def test_a_part_in_storage_has_no_bike_prefix(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    spare = component_service.create_component(name="Spare chain", component_type="chain")
    schedule_service.create_schedule(component_id=spare.id, name="Re-wax", interval_days=30)

    (item,) = schedule_service.list_due_overview()

    assert item.bike_name is None
