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
