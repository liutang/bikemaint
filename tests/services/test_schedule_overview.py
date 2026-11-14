"""A bike's or part's schedules, worded for the Schedules page (specs/056-schedules-page)."""

import pytest

from app.db import connection
from app.services import bike_service, component_service, schedule_service


@pytest.fixture
def db_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _typed(**kw):
    return {"service_type": "Lube/Wax", "interval_kind": "usage", "interval_unit": "miles", "interval_value": 186, **kw}


@pytest.mark.parametrize(
    "kw,text",
    [
        ({}, "Every 186 miles"),
        ({"interval_value": 1, "interval_unit": "rides"}, "Every 1 ride"),
        ({"interval_value": 2.5, "interval_unit": "hours"}, "Every 2.5 hours"),
        ({"interval_kind": "period", "interval_unit": "months", "interval_value": 4}, "Every 4 months"),
        ({"interval_kind": "period", "interval_unit": "weeks", "interval_value": 1}, "Every 1 week"),
    ],
)
def test_interval_text_for_typed_schedules(db_ready, kw, text):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(bike_id=bike.id, **_typed(**kw))

    assert schedule_service.interval_text(schedule) == text


def test_interval_text_for_older_schedules(db_ready):
    bike = bike_service.create_bike(name="Road")
    miles = schedule_service.create_schedule(bike_id=bike.id, name="Chain", interval_miles=500)
    days = schedule_service.create_schedule(bike_id=bike.id, name="Check", interval_days=30)
    both = schedule_service.create_schedule(bike_id=bike.id, name="Both", interval_miles=500, interval_days=30)

    assert schedule_service.interval_text(miles) == "Every 500 miles"
    assert schedule_service.interval_text(days) == "Every 30 days"
    assert schedule_service.interval_text(both) == "Every 500 miles or 30 days"


def test_overview_is_only_this_owners_active_schedules_in_order(db_ready):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    first = schedule_service.create_schedule(component_id=chain.id, **_typed())
    second = schedule_service.create_schedule(component_id=chain.id, **_typed(service_type="Clean"))
    schedule_service.create_schedule(bike_id=bike.id, **_typed(service_type="Check"))  # another owner
    gone = schedule_service.create_schedule(component_id=chain.id, **_typed(service_type="Topup"))
    schedule_service.delete_schedule(gone.id)

    items = schedule_service.list_overview_for_owner("component", chain.id)

    assert [i.schedule.id for i in items] == [first.id, second.id]
    assert all(i.owner_type == "component" for i in items)
    assert [i.schedule.id for i in schedule_service.list_overview_for_owner("bike", bike.id)] == [3]
