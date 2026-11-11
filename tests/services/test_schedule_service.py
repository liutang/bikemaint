from datetime import date, datetime, timedelta, timezone

import pytest

from app.db import connection
from app.db import mileage as mileage_db
from app.services import bike_service, component_service, maintenance_service, schedule_service

TODAY = date.today()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


_activity_ids = iter(range(1, 10_000))


def _ride_history(bike, *, ride_days: int, miles_per_ride: float):
    """Insert `ride_days` rides on distinct recent days, then refresh the bike's total."""
    with connection.get_connection() as conn:
        for days_ago in range(1, ride_days + 1):
            occurred = datetime.now(timezone.utc) - timedelta(days=days_ago)
            mileage_db.upsert_ride_activity(
                conn,
                strava_activity_id=next(_activity_ids),
                strava_gear_id="g1",
                bike_id=bike.id,
                distance_miles=miles_per_ride,
                occurred_at=occurred.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)


def _steady_bike(name="Road Bike", miles_per_day=1.0):
    """A bike with 10 ride-days in the 90-day window and a pace of `miles_per_day`."""
    bike = bike_service.create_bike(name=name)
    _ride_history(bike, ride_days=10, miles_per_ride=miles_per_day * 90 / 10)
    return bike_service.get_bike(bike.id)


def test_mileage_interval_projects_due_date_from_trailing_pace(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_miles=100
    )

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at == TODAY + timedelta(days=100)
    assert projection.remaining_miles == pytest.approx(100.0)
    assert projection.is_low_confidence is False
    assert projection.is_overdue is False


def test_time_interval_projects_due_date_from_baseline_date(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Annual service", interval_days=365, today=TODAY
    )

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at == TODAY + timedelta(days=365)
    assert projection.is_low_confidence is False


def test_when_both_intervals_are_set_the_sooner_due_date_wins(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    mileage_sooner = schedule_service.create_schedule(
        bike_id=bike.id, name="A", interval_miles=50, interval_days=90, today=TODAY
    )
    time_sooner = schedule_service.create_schedule(
        bike_id=bike.id, name="B", interval_miles=200, interval_days=30, today=TODAY
    )

    assert schedule_service.project_due_date(mileage_sooner, today=TODAY).due_at == TODAY + timedelta(days=50)
    assert schedule_service.project_due_date(time_sooner, today=TODAY).due_at == TODAY + timedelta(days=30)


def test_schedule_past_its_mileage_interval_is_overdue(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_miles=100
    )
    _ride_history(bike, ride_days=1, miles_per_ride=150)  # total now exceeds baseline + interval

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.is_overdue is True
    assert projection.due_at == TODAY


def test_no_ride_history_with_mileage_only_interval_is_low_confidence_without_a_date(db_path):
    bike = bike_service.create_bike(name="New Bike")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_miles=100
    )

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at is None
    assert projection.is_low_confidence is True


def test_no_ride_history_with_both_intervals_falls_back_to_time_only(db_path):
    bike = bike_service.create_bike(name="New Bike")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Service", interval_miles=500, interval_days=60, today=TODAY
    )

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at == TODAY + timedelta(days=60)
    assert projection.is_low_confidence is False


def test_sparse_ride_history_gives_a_date_but_flags_it_low_confidence(db_path):
    bike = bike_service.create_bike(name="New Bike")
    _ride_history(bike, ride_days=2, miles_per_ride=9.0)
    bike = bike_service.get_bike(bike.id)
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_miles=100
    )

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at is not None
    assert projection.is_low_confidence is True


def test_component_projection_follows_its_current_bikes_pace_then_storage(db_path):
    slow_bike = _steady_bike("Slow", miles_per_day=1.0)
    fast_bike = _steady_bike("Fast", miles_per_day=2.0)
    component = component_service.create_component(
        name="Chain", component_type="chain", parent_bike_id=slow_bike.id
    )
    schedule = schedule_service.create_schedule(
        component_id=component.id, name="Replace chain", interval_miles=100
    )

    on_slow = schedule_service.project_due_date(schedule, today=TODAY)
    component_service.move_component(component.id, parent_bike_id=fast_bike.id)
    on_fast = schedule_service.project_due_date(schedule, today=TODAY)
    component_service.move_component(component.id)  # into storage
    in_storage = schedule_service.project_due_date(schedule, today=TODAY)

    assert on_slow.due_at == TODAY + timedelta(days=100)
    assert on_fast.due_at == TODAY + timedelta(days=50)
    assert in_storage.due_at is None
    assert in_storage.is_low_confidence is True


def test_nested_component_uses_the_pace_of_the_bike_at_the_top_of_its_chain(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    wheel = component_service.create_component(
        name="Wheel", component_type="wheel", parent_bike_id=bike.id
    )
    rim = component_service.create_component(
        name="Rim", component_type="rim", parent_component_id=wheel.id
    )
    tire = component_service.create_component(
        name="Tire", component_type="tire", parent_component_id=rim.id
    )
    schedule = schedule_service.create_schedule(
        component_id=tire.id, name="Replace tire", interval_miles=100
    )

    assert schedule_service.project_due_date(schedule, today=TODAY).due_at == TODAY + timedelta(
        days=100
    )


def test_complete_schedule_logs_maintenance_bumps_cycle_and_resets_baseline(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_miles=100
    )
    assert schedule.cycle_number == 1
    _ride_history(bike, ride_days=1, miles_per_ride=40)
    current_total = bike_service.get_bike(bike.id).total_mileage

    completed = schedule_service.complete_schedule(schedule.id, today=TODAY)

    assert completed.cycle_number == 2
    assert completed.baseline_mileage == pytest.approx(current_total)
    assert completed.baseline_date == TODAY.isoformat()
    history = maintenance_service.list_for_bike(bike.id)
    assert len(history) == 1
    assert history[0].description == "Replace chain"
    assert history[0].schedule_id == schedule.id
    assert history[0].performed_at == TODAY.isoformat()
    assert history[0].mileage_at_service == pytest.approx(current_total)
    next_projection = schedule_service.project_due_date(completed, today=TODAY)
    assert next_projection.remaining_miles == pytest.approx(100.0)


def test_complete_unknown_schedule_raises_lookup_error(db_path):
    with pytest.raises(LookupError):
        schedule_service.complete_schedule(999)


def test_create_schedule_requires_an_interval_and_exactly_one_owner(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    component = component_service.create_component(name="Chain", component_type="chain")

    with pytest.raises(ValueError):
        schedule_service.create_schedule(bike_id=bike.id, name="No interval")
    with pytest.raises(ValueError):
        schedule_service.create_schedule(name="No owner", interval_days=30)
    with pytest.raises(ValueError):
        schedule_service.create_schedule(
            bike_id=bike.id, component_id=component.id, name="Both", interval_days=30
        )


def test_deleted_schedule_drops_off_the_active_lists_but_keeps_history(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Service", interval_days=30)
    schedule_service.complete_schedule(schedule.id, today=TODAY)

    schedule_service.delete_schedule(schedule.id)

    assert schedule_service.list_for_bike(bike.id) == []
    assert len(maintenance_service.list_for_bike(bike.id)) == 1


def test_due_overview_lists_every_owner_most_urgent_first(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    component = component_service.create_component(name="Chain", component_type="chain")
    later = schedule_service.create_schedule(
        bike_id=bike.id, name="Annual", interval_days=365, today=TODAY
    )
    sooner = schedule_service.create_schedule(
        component_id=component.id, name="Wax", interval_days=10, today=TODAY
    )

    overview = schedule_service.list_due_overview(today=TODAY)

    assert [item.schedule.id for item in overview] == [sooner.id, later.id]
    assert overview[0].owner_type == "component"
    assert overview[0].owner_name == "Chain"
    assert overview[1].owner_type == "bike"
    assert overview[1].owner_name == "Road Bike"


def test_deleting_bike_with_active_schedule_requires_confirmation(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    schedule_service.create_schedule(bike_id=bike.id, name="Service", interval_days=30)

    with pytest.raises(bike_service.ConfirmationRequiredError):
        bike_service.delete_bike(bike.id)

    bike_service.delete_bike(bike.id, confirmed=True)


def test_deleting_component_with_active_schedule_requires_confirmation(db_path):
    component = component_service.create_component(name="Chain", component_type="chain")
    schedule_service.create_schedule(component_id=component.id, name="Wax", interval_days=30)

    with pytest.raises(component_service.ConfirmationRequiredError):
        component_service.delete_component(component.id)

    component_service.delete_component(component.id, confirmed=True)
