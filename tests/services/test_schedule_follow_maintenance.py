"""Logging maintenance restarts the matching schedules (specs/046)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_service, maintenance_service, schedule_service

TODAY = date.today()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _wheel_with_old_topup_schedule():
    wheel = component_service.create_component(name="Wheel", component_type="wheel")
    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2023-09-01")
    schedule = schedule_service.create_schedule(
        component_id=wheel.id, service_type="Topup", interval_kind="period", interval_value=4, interval_unit="months"
    )
    return wheel, schedule


def _now(schedule_id):
    return schedule_service.get_schedule(schedule_id)


def test_logging_a_newer_topup_moves_the_schedule_out_and_starts_a_new_cycle(db_path):
    # The rider's case: 1048 days late, then a Topup is logged for 2/23/2024.
    wheel, schedule = _wheel_with_old_topup_schedule()
    assert schedule_service.project_due_date(schedule, today=TODAY).is_overdue is True

    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2024-02-23")

    after = _now(schedule.id)
    assert (after.baseline_date, after.cycle_number) == ("2024-02-23", schedule.cycle_number + 1)
    assert schedule_service.project_due_date(after, today=TODAY).due_at == date(2024, 6, 23)


def test_a_recent_topup_makes_it_on_track(db_path):
    wheel, schedule = _wheel_with_old_topup_schedule()

    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at=TODAY.isoformat())

    projection = schedule_service.project_due_date(_now(schedule.id), today=TODAY)
    assert projection.is_overdue is False


def test_an_older_entry_other_type_or_other_owner_changes_nothing(db_path):
    wheel, schedule = _wheel_with_old_topup_schedule()
    other = component_service.create_component(name="Other", component_type="wheel")
    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2022-01-01")
    maintenance_service.log_maintenance(component_id=wheel.id, description="Check", performed_at="2026-01-01")
    maintenance_service.log_maintenance(component_id=other.id, description="Topup", performed_at="2026-01-01")

    after = _now(schedule.id)

    assert (after.baseline_date, after.cycle_number) == ("2023-09-01", schedule.cycle_number)


def test_editing_an_entry_to_a_newer_date_rebases_without_a_new_cycle(db_path):
    wheel, schedule = _wheel_with_old_topup_schedule()
    entry = maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2023-10-01")
    cycle = _now(schedule.id).cycle_number

    maintenance_service.update_entry(entry.id, description="Topup", performed_at="2024-05-01", mileage_at_service=0.0)

    after = _now(schedule.id)
    assert (after.baseline_date, after.cycle_number) == ("2024-05-01", cycle)


def test_marking_done_restarts_the_schedule_once(db_path):
    wheel, schedule = _wheel_with_old_topup_schedule()

    done = schedule_service.complete_schedule(schedule.id, today=TODAY)

    assert done.cycle_number == schedule.cycle_number + 1 and done.baseline_date == TODAY.isoformat()


def test_a_newer_service_restarts_usage_counting_from_that_entry(db_path):
    bike = bike_service.create_bike(name="Road")
    with connection.get_connection() as conn:
        for n, when in enumerate(["2026-01-10T08:00:00.000000Z", "2026-03-10T08:00:00.000000Z"]):
            mileage_db.upsert_ride_activity(
                conn, strava_activity_id=70 + n, strava_gear_id="g", bike_id=bike.id, distance_miles=5,
                occurred_at=when, moving_time_seconds=3600,
            )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="usage", interval_value=10, interval_unit="rides"
    )
    assert schedule_service.project_due_date(schedule, today=TODAY).remaining == 8

    maintenance_service.log_maintenance(bike_id=bike.id, description="Check", performed_at="2026-02-01")

    assert schedule_service.project_due_date(_now(schedule.id), today=TODAY).remaining == 9  # 1 ride since


def test_new_rides_show_in_the_projection_without_any_other_change(db_path):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="usage", interval_value=10, interval_unit="rides"
    )
    before = schedule_service.project_due_date(schedule, today=TODAY).remaining
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=80, strava_gear_id="g", bike_id=bike.id, distance_miles=5,
            occurred_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

    assert schedule_service.project_due_date(_now(schedule.id), today=TODAY).remaining == before - 1


def _insert_entry_directly(owner_column, owner_id, service, day):
    """An entry that bypassed the service (as ones logged before feature 046 did)."""
    with connection.get_connection() as conn:
        conn.execute(
            f"INSERT INTO maintenance_log_entry ({owner_column}, description, performed_at, mileage_at_service,"
            " kind, created_at, updated_at) VALUES (?, ?, ?, 0, 'service', 'x', 'x')",
            (owner_id, service, day),
        )


def test_a_projection_counts_from_the_latest_matching_entry_even_if_the_schedule_was_never_restarted(db_path):
    # The rider's report: stuck on 9/1/2023 although Topups were logged on 2/23/2024 and 6/29/2024.
    wheel, schedule = _wheel_with_old_topup_schedule()
    _insert_entry_directly("component_id", wheel.id, "Topup", "2024-02-23")
    _insert_entry_directly("component_id", wheel.id, "Topup", "2024-06-29")

    projection = schedule_service.project_due_date(_now(schedule.id), today=TODAY)

    assert projection.due_at == date(2024, 10, 29)
    item = schedule_service.get_due_item(schedule.id, today=TODAY)
    assert item.days_until == (date(2024, 10, 29) - TODAY).days


def test_an_entry_older_than_the_saved_starting_point_does_not_pull_a_schedule_back(db_path):
    wheel, schedule = _wheel_with_old_topup_schedule()
    maintenance_service.log_maintenance(component_id=wheel.id, description="Topup", performed_at="2025-05-01")
    _insert_entry_directly("component_id", wheel.id, "Topup", "2024-01-01")

    assert schedule_service.project_due_date(_now(schedule.id), today=TODAY).due_at == date(2025, 9, 1)

