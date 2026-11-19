from datetime import date, datetime, timedelta, timezone

import pytest

from app.db import connection
from app.db import mileage as mileage_db
from app.services import bike_service, component_service, maintenance_service, schedule_service
from app.services import clock_service as _clock  # "today" is the saved zone's date (specs/075)

TODAY = _clock.today()


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
    """A bike ridden steadily for 90 days (10 rides, the first 89 days ago) at `miles_per_day`.

    Its 90-day pace and its whole-history pace are equal, so the blended pace (specs/085) is
    `miles_per_day`, and with 10 rides over 90 days the estimate is trusted.
    """
    bike = bike_service.create_bike(name=name)
    with connection.get_connection() as conn:
        for days_ago in range(89, 7, -9):  # 89, 80, ..., 8: ten rides
            when = datetime.combine(TODAY - timedelta(days=days_ago), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
            mileage_db.upsert_ride_activity(
                conn, strava_activity_id=next(_activity_ids), strava_gear_id="g1", bike_id=bike.id,
                distance_miles=miles_per_day * 90 / 10, occurred_at=when.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)
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


# ------------------------------------------------ mark done guard and notice (specs/006, M2)


def test_a_repeat_completion_within_a_few_seconds_logs_only_once(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14)

    first = schedule_service.complete_schedule(schedule.id)
    second = schedule_service.complete_schedule(schedule.id)  # a double click

    assert first.cycle_number == 2 and second.cycle_number == 2
    entries = [e for e in maintenance_service.list_for_bike(bike.id) if e.schedule_id == schedule.id]
    assert len(entries) == 1


def test_completing_again_after_the_window_logs_a_second_entry(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14)
    schedule_service.complete_schedule(schedule.id)
    with connection.get_connection() as conn:  # pretend that was a minute ago
        conn.execute("UPDATE maintenance_log_entry SET created_at = '2000-01-01T00:00:00.000000Z'")

    again = schedule_service.complete_schedule(schedule.id)

    assert again.cycle_number == 3
    assert len([e for e in maintenance_service.list_for_bike(bike.id) if e.schedule_id == schedule.id]) == 2


def test_completion_guard_is_per_schedule(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    a = schedule_service.create_schedule(bike_id=bike.id, name="A", interval_days=14)
    b = schedule_service.create_schedule(bike_id=bike.id, name="B", interval_days=14)

    schedule_service.complete_schedule(a.id)
    schedule_service.complete_schedule(b.id)

    assert len([e for e in maintenance_service.list_for_bike(bike.id) if e.schedule_id])== 2


def test_next_due_text_names_the_date_or_the_mileage(db_path):
    bike = _steady_bike(miles_per_day=1.0)
    dated = schedule_service.create_schedule(bike_id=bike.id, name="Dated", interval_days=14)
    mileage_only = schedule_service.create_schedule(bike_id=bike.id, name="Miles", interval_miles=500)

    dated_item = schedule_service.get_due_item(dated.id)
    miles_item = schedule_service.get_due_item(mileage_only.id)

    assert schedule_service.next_due_text(dated_item) == f"Next due {dated_item.projection.due_at.isoformat()}"
    assert schedule_service.next_due_text(miles_item).startswith("Next due")


# ------------------------------------------------ specs/075 US5: today is the rider's date


EVENING_UTC = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)  # 8:00 PM EST on Nov 16


@pytest.fixture
def evening_in_new_york(db_path, new_york, monkeypatch):
    from app.services import clock_service

    monkeypatch.setattr(clock_service, "_utc_now", lambda: EVENING_UTC)


def test_days_left_count_from_the_riders_date(evening_in_new_york):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="period", interval_value=1, interval_unit="weeks"
    )
    with connection.get_connection() as conn:
        conn.execute("UPDATE maintenance_schedule SET baseline_date = '2026-11-09' WHERE id = ?", (schedule.id,))

    projection = schedule_service.project_due_date(schedule_service.get_schedule(schedule.id))

    assert projection.due_at == date(2026, 11, 16) and projection.is_overdue is False  # due today, not yesterday


def test_mark_done_in_the_evening_dates_the_entry_today(evening_in_new_york):
    bike = bike_service.create_bike(name="Road")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="period", interval_value=1, interval_unit="weeks"
    )

    done = schedule_service.complete_schedule(schedule.id)

    assert done.baseline_date == "2026-11-16"
    assert maintenance_service.list_for_bike_rows(bike.id)[0].entry.performed_at == "2026-11-16"


def test_a_new_schedule_with_no_history_starts_on_the_local_dates(evening_in_new_york):
    from app.services import component_history_service as history

    bike = bike_service.create_bike(name="Road")
    part = component_service.create_component(name="Chain", component_type="chain")
    history.log_period(part.id, bike_id=bike.id, installed_at="2026-11-02T03:00:00.000000Z",  # 10 PM EST on Nov 1
                       removed_at="2026-11-03T03:00:00.000000Z")
    with connection.get_connection() as conn:  # added at 9 PM EST on Nov 16
        conn.execute("UPDATE bike SET created_at = '2026-11-17T02:00:00.000000Z' WHERE id = ?", (bike.id,))

    on_part = schedule_service.create_schedule(
        component_id=part.id, service_type="Check", interval_kind="period", interval_value=1, interval_unit="months"
    )
    on_bike = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Clean", interval_kind="period", interval_value=1, interval_unit="months"
    )

    assert on_part.baseline_date == "2026-11-01"
    assert on_bike.baseline_date == "2026-11-16"


def test_the_trailing_pace_window_starts_at_local_midnight(evening_in_new_york):
    bike = bike_service.create_bike(name="Road")
    with connection.get_connection() as conn:  # 11 PM EDT on Aug 17 is 03:00 UTC on Aug 18
        mileage_db.upsert_ride_activity(conn, strava_activity_id=1, strava_gear_id="g", bike_id=bike.id,
                                        distance_miles=90, occurred_at="2026-08-18T03:00:00.000000Z")
        pace, _ = schedule_service._pace(conn, bike.id, date(2026, 11, 16), "miles")

    # The 90-day window starts at local midnight on Aug 18 (04:00 UTC), so the ride isn't in it; the
    # whole history starts on its local date, Aug 17, which is 92 days to Nov 16 inclusive (specs/085).
    assert pace == pytest.approx((0 + 90 / 92) / 2)


# ------------------------------------------------ specs/085: the blended pace


def _ride_on(bike, days_ago, miles, seconds=None):
    when = datetime.combine(TODAY - timedelta(days=days_ago), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=next(_activity_ids), strava_gear_id="g1", bike_id=bike.id,
                                        distance_miles=miles, occurred_at=when.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                        moving_time_seconds=seconds)
        mileage_db.recompute_bike_total_mileage(conn, bike.id)


def test_the_specs_example_blends_90_days_and_the_whole_history(db_path):
    """28.7 mi in 90 days, 1,353.5 mi over 2,040 days, 23.3 mi left: due in 48 days (spec SC-001)."""
    bike = bike_service.create_bike(name="Revolt")
    _ride_on(bike, 2039, 300.0)
    _ride_on(bike, 2000, 300.0)
    _ride_on(bike, 1000, 724.8)
    _ride_on(bike, 30, 15.0)
    _ride_on(bike, 10, 13.7)
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Lube", interval_miles=23.3)

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at == TODAY + timedelta(days=48)
    assert projection.is_low_confidence is False


def test_no_rides_in_90_days_uses_half_the_whole_history_pace(db_path):
    bike = bike_service.create_bike(name="Winter")
    _ride_on(bike, 400, 100.0)
    _ride_on(bike, 200, 100.0)  # 200 mi over 401 days, nothing in the last 90
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Lube", interval_miles=10)
    pace = (200 / 401) / 2
    assert schedule_service.project_due_date(schedule, today=TODAY).due_at == TODAY + timedelta(days=__import__("math").ceil(10 / pace - 1e-9))


def test_hours_whole_history_starts_at_the_first_timed_ride(db_path):
    bike = bike_service.create_bike(name="Road")
    _ride_on(bike, 1000, 50.0)               # no moving time: before times were recorded
    _ride_on(bike, 179, 10.0, seconds=36000)  # 10 h; the timed history is 180 days
    schedule = schedule_service.create_schedule(bike_id=bike.id, service_type="Service", interval_kind="usage",
                                                interval_value=5, interval_unit="hours")
    hours_pace = (0 / 90 + 10 / 180) / 2  # nothing timed in 90 days
    projection = schedule_service.project_due_date(schedule, today=TODAY)
    left = projection.remaining
    assert projection.due_at == TODAY + timedelta(days=__import__("math").ceil(left / hours_pace - 1e-9))


@pytest.mark.parametrize("rides,first_days_ago,low", [(4, 200, True), (5, 200, False), (6, 28, True), (6, 29, False)])
def test_low_confidence_means_too_little_history(db_path, rides, first_days_ago, low):
    bike = bike_service.create_bike(name="New")
    _ride_on(bike, first_days_ago, 10.0)
    for i in range(rides - 1):
        _ride_on(bike, i, 10.0)
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Lube", interval_miles=500)
    assert schedule_service.project_due_date(schedule, today=TODAY).is_low_confidence is low
