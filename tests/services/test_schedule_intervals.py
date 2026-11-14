"""Service types, one interval of any unit, recurring and notify flags (specs/040)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.db import connection
from app.db import mileage as mileage_db
from app.services import bike_service, component_history_service as history, component_service, schedule_service

TODAY = date.today()
_ids = iter(range(1, 10_000))


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _rides(bike, *, days, seconds=3600, miles=10.0):
    """One ride on each of the last `days` days (so a 90-day pace exists)."""
    with connection.get_connection() as conn:
        for ago in range(1, days + 1):
            when = (datetime.now(timezone.utc) - timedelta(days=ago)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            mileage_db.upsert_ride_activity(
                conn, strava_activity_id=next(_ids), strava_gear_id="g", bike_id=bike.id,
                distance_miles=miles, occurred_at=when, moving_time_seconds=seconds,
            )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)


def _typed(bike_id=None, component_id=None, **kw):
    args = dict(service_type="Check", interval_kind="usage", interval_value=20, interval_unit="rides")
    return schedule_service.create_schedule(bike_id=bike_id, component_id=component_id, **{**args, **kw})


@pytest.mark.parametrize("start,value,unit,expected", [
    (date(2026, 1, 31), 1, "months", date(2026, 2, 28)),
    (date(2026, 1, 15), 13, "months", date(2027, 2, 15)),
    (date(2024, 2, 29), 1, "years", date(2025, 2, 28)),
    (date(2026, 3, 1), 2, "years", date(2028, 3, 1)),
    (date(2026, 3, 1), 3, "weeks", date(2026, 3, 22)),
])
def test_period_arithmetic_uses_calendar_units(start, value, unit, expected):
    assert schedule_service.add_period(start, value, unit) == expected


def test_a_period_schedule_is_due_the_interval_after_its_baseline(db_path):
    bike = bike_service.create_bike(name="Road")

    schedule = _typed(bike.id, service_type="Service", interval_kind="period", interval_value=3, interval_unit="months")

    assert (schedule.name, schedule.service_type) == ("Service", "Service")
    projection = schedule_service.project_due_date(schedule, today=TODAY)
    assert projection.due_at == schedule_service.add_period(TODAY, 3, "months")
    assert projection.is_low_confidence is False


def test_a_rides_schedule_projects_from_the_rides_per_day(db_path):
    bike = bike_service.create_bike(name="Road")
    _rides(bike, days=10)
    _log(bike, "Check", TODAY.isoformat())  # counting starts after the last service
    schedule = _typed(bike.id, interval_value=20, interval_unit="rides")  # nothing used yet

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    # 10 rides in 90 days is 1/9 per day, so 20 rides take 180 days.
    assert projection.due_at == TODAY + timedelta(days=180)
    assert (projection.remaining, projection.remaining_unit) == (20, "rides")
    assert projection.remaining_miles is None


def test_an_hours_schedule_projects_from_moving_time(db_path):
    bike = bike_service.create_bike(name="Road")
    _rides(bike, days=10, seconds=3600)
    _log(bike, "Check", TODAY.isoformat())  # counting starts after the last service
    schedule = _typed(bike.id, interval_value=5, interval_unit="hours")

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.due_at == TODAY + timedelta(days=45)  # 10 h in 90 days, 5 h to go
    assert (projection.remaining, projection.remaining_unit) == (5, "hours")


def test_used_up_rides_or_hours_make_the_schedule_overdue(db_path):
    bike = bike_service.create_bike(name="Road")
    rides = _typed(bike.id, interval_value=3, interval_unit="rides")
    hours = _typed(bike.id, interval_value=2, interval_unit="hours")
    with connection.get_connection() as conn:
        conn.execute("UPDATE maintenance_schedule SET baseline_at = '2000-01-01T00:00:00.000000Z'")
    _rides(bike, days=3, seconds=3600)

    for schedule in (schedule_service.get_schedule(rides.id), schedule_service.get_schedule(hours.id)):
        projection = schedule_service.project_due_date(schedule, today=TODAY)
        assert projection.is_overdue is True and projection.due_at == TODAY


def test_rides_before_the_baseline_do_not_count(db_path):
    bike = bike_service.create_bike(name="Road")
    _rides(bike, days=5)
    _log(bike, "Check", TODAY.isoformat())  # counting starts after the last service
    schedule = _typed(bike.id, interval_value=5, interval_unit="rides")  # baseline is now

    assert schedule_service.project_due_date(schedule, today=TODAY).remaining == 5


def test_a_part_counts_only_rides_while_it_was_installed(db_path):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    schedule = _typed(component_id=chain.id, interval_value=10, interval_unit="rides")
    with connection.get_connection() as conn:
        conn.execute("UPDATE maintenance_schedule SET baseline_at = '2000-01-01T00:00:00.000000Z'")
        conn.execute("UPDATE component_installation_period SET installed_at = ?",
                     ((datetime.now(timezone.utc) - timedelta(days=3, hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),))
    _rides(bike, days=10)  # only the 3 most recent are after it went on

    projection = schedule_service.project_due_date(schedule_service.get_schedule(schedule.id), today=TODAY)

    assert projection.remaining == 7


def test_the_miles_unit_still_reports_remaining_miles(db_path):
    bike = bike_service.create_bike(name="Road")
    _rides(bike, days=10, miles=9.0)
    _log(bike, "Check", TODAY.isoformat())  # counting starts after the last service
    schedule = _typed(bike.id, interval_value=100, interval_unit="miles")

    projection = schedule_service.project_due_date(schedule, today=TODAY)

    assert projection.remaining_miles == pytest.approx(100.0)
    assert (projection.remaining, projection.remaining_unit) == (pytest.approx(100.0), "miles")


@pytest.mark.parametrize("kw", [
    {"service_type": "Polish"},
    {"interval_kind": "usage", "interval_unit": "months"},
    {"interval_kind": "period", "interval_unit": "miles"},
    {"interval_value": 0}, {"interval_value": -1},
    {"interval_unit": "rides", "interval_value": 2.5},
    {"interval_kind": "period", "interval_unit": "weeks", "interval_value": 1.5},
])
def test_invalid_typed_schedules_are_refused(db_path, kw):
    bike = bike_service.create_bike(name="Road")

    with pytest.raises(ValueError):
        _typed(bike.id, **kw)


def test_weeks_and_miles_also_fill_the_old_interval_columns(db_path):
    bike = bike_service.create_bike(name="Road")

    weeks = _typed(bike.id, interval_kind="period", interval_value=2, interval_unit="weeks")
    miles = _typed(bike.id, interval_value=150, interval_unit="miles")

    assert (weeks.interval_days, weeks.interval_miles) == (14, None)
    assert (miles.interval_miles, miles.interval_days) == (150.0, None)


def test_a_recurring_schedule_starts_its_next_cycle_when_done(db_path):
    bike = bike_service.create_bike(name="Road")
    schedule = _typed(bike.id)

    done = schedule_service.complete_schedule(schedule.id, today=TODAY)

    assert (done.cycle_number, done.is_active) == (2, True)
    assert done.baseline_at is not None and done.baseline_at > schedule.baseline_at


def test_a_one_time_schedule_ends_when_done_but_its_maintenance_is_logged(db_path):
    from app.services import maintenance_service

    bike = bike_service.create_bike(name="Road")
    schedule = _typed(bike.id, service_type="Replace", is_recurring=False)

    done = schedule_service.complete_schedule(schedule.id, today=TODAY)

    assert done.is_active is False and done.cycle_number == 1
    assert [e.description for e in maintenance_service.list_for_bike(bike.id)] == ["Replace"]
    assert schedule_service.list_due_overview(today=TODAY) == []


def test_an_old_schedule_is_converted_by_the_rider_and_keeps_its_cycle(db_path):
    bike = bike_service.create_bike(name="Road")
    old = schedule_service.create_schedule(bike_id=bike.id, name="lube the chain", interval_miles=200)

    new = schedule_service.update_schedule(
        old.id, service_type="Lube/Wax", interval_kind="usage", interval_value=200, interval_unit="miles",
        is_recurring=True, notify=False,
    )

    assert (new.name, new.service_type, new.interval_unit, new.notify) == ("Lube/Wax", "Lube/Wax", "miles", False)
    assert (new.cycle_number, new.baseline_mileage, new.baseline_date) == (old.cycle_number, old.baseline_mileage, old.baseline_date)


def test_next_due_text_names_the_unit(db_path):
    bike = bike_service.create_bike(name="Road")
    schedule = _typed(bike.id, interval_value=20, interval_unit="rides")
    item = schedule_service.get_due_item(schedule.id, today=TODAY)

    assert schedule_service.next_due_text(item) == "Next due after 20 more rides"


# ---- 040 FR-011: a new schedule counts from the last matching service, else from when tracking began


def _log(owner, service, day, time=None, mileage=None):
    from app.services import maintenance_service

    key = "bike_id" if hasattr(owner, "bike_type") else "component_id"
    return maintenance_service.log_maintenance(
        **{key: owner.id}, description=service, performed_at=day, performed_time=time, mileage_at_service=mileage
    )


def test_a_period_schedule_counts_from_the_last_matching_service(db_path):
    # The rider's case: a Topup logged in 2023, then "Topup every 4 months", is overdue at once.
    wheel = component_service.create_component(name="Wheel", component_type="wheel")
    _log(wheel, "Topup", "2023-09-01")

    schedule = _typed(component_id=wheel.id, service_type="Topup", interval_kind="period", interval_value=4, interval_unit="months")

    projection = schedule_service.project_due_date(schedule, today=TODAY)
    assert projection.due_at == date(2024, 1, 1) and projection.is_overdue is True
    item = schedule_service.get_due_item(schedule.id, today=TODAY)
    assert item.status == "overdue"


def test_only_the_same_service_type_on_the_same_owner_counts_and_the_latest_wins(db_path):
    wheel = component_service.create_component(name="Wheel", component_type="wheel")
    other = component_service.create_component(name="Other", component_type="wheel")
    _log(wheel, "Check", "2023-01-01")        # another type: ignored
    _log(other, "Topup", "2023-01-01")        # another part: ignored
    _log(wheel, "Topup", "2024-01-10")
    _log(wheel, "Topup", "2025-03-05")        # the latest

    schedule = _typed(component_id=wheel.id, service_type="Topup", interval_kind="period", interval_value=2, interval_unit="months")

    assert schedule.baseline_date == "2025-03-05"
    assert schedule_service.project_due_date(schedule, today=TODAY).due_at == date(2025, 5, 5)


def test_a_miles_schedule_counts_miles_since_the_last_matching_service(db_path):
    bike = bike_service.create_bike(name="Road", manual_baseline_mileage=500.0)
    with connection.get_connection() as conn:
        for n, (when, miles) in enumerate([("2026-01-10T08:00:00.000000Z", 40), ("2026-03-10T08:00:00.000000Z", 70)]):
            mileage_db.upsert_ride_activity(conn, strava_activity_id=900 + n, strava_gear_id="g", bike_id=bike.id,
                                            distance_miles=miles, occurred_at=when)
        mileage_db.recompute_bike_total_mileage(conn, bike.id)
    _log(bike, "Lube/Wax", "2026-02-01")   # mileage then: 500 + 40 = 540

    schedule = _typed(bike.id, service_type="Lube/Wax", interval_value=50, interval_unit="miles")

    projection = schedule_service.project_due_date(schedule, today=TODAY)
    assert projection.is_overdue is True  # 70 mi since the service, interval 50


def test_rides_and_hours_count_only_after_the_last_matching_service(db_path):
    bike = bike_service.create_bike(name="Road")
    with connection.get_connection() as conn:
        for n, (when, secs) in enumerate([("2026-01-10T08:00:00.000000Z", 3600), ("2026-03-10T08:00:00.000000Z", 7200),
                                          ("2026-03-11T08:00:00.000000Z", 7200)]):
            mileage_db.upsert_ride_activity(conn, strava_activity_id=950 + n, strava_gear_id="g", bike_id=bike.id,
                                            distance_miles=5, occurred_at=when, moving_time_seconds=secs)
    _log(bike, "Check", "2026-02-01")

    rides = _typed(bike.id, service_type="Check", interval_value=10, interval_unit="rides")
    hours = _typed(bike.id, service_type="Check", interval_value=10, interval_unit="hours")

    assert schedule_service.project_due_date(rides, today=TODAY).remaining == 8     # 2 rides since
    assert schedule_service.project_due_date(hours, today=TODAY).remaining == 6     # 4 h since


def test_with_no_matching_service_usage_counts_all_rides_but_not_the_starting_mileage(db_path):
    bike = bike_service.create_bike(name="Road", manual_baseline_mileage=1000.0)
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=990, strava_gear_id="g", bike_id=bike.id,
                                        distance_miles=30, occurred_at="2025-05-01T08:00:00.000000Z", moving_time_seconds=3600)
        mileage_db.recompute_bike_total_mileage(conn, bike.id)

    miles = _typed(bike.id, service_type="Clean", interval_value=20, interval_unit="miles")
    rides = _typed(bike.id, service_type="Clean", interval_value=5, interval_unit="rides")

    assert schedule_service.project_due_date(miles, today=TODAY).is_overdue is True        # 30 of 20 used
    assert schedule_service.project_due_date(rides, today=TODAY).remaining == 4            # 1 ride used


def test_with_no_matching_service_a_period_counts_from_the_earliest_install_else_when_it_was_added(db_path):
    bike = bike_service.create_bike(name="Road")
    old = component_service.create_component(name="Old chain", component_type="chain", parent_bike_id=bike.id)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2023-01-01T00:00:00.000000Z' WHERE component_id = ?", (old.id,))
    fresh = component_service.create_component(name="New chain", component_type="chain")

    stale = _typed(component_id=old.id, service_type="Clean", interval_kind="period", interval_value=4, interval_unit="months")
    new = _typed(component_id=fresh.id, service_type="Clean", interval_kind="period", interval_value=4, interval_unit="months")

    assert schedule_service.project_due_date(stale, today=TODAY).is_overdue is True
    assert schedule_service.project_due_date(new, today=TODAY).is_overdue is False
    assert new.baseline_date == TODAY.isoformat()


def test_marking_done_still_restarts_from_now(db_path):
    wheel = component_service.create_component(name="Wheel", component_type="wheel")
    _log(wheel, "Topup", "2023-09-01")
    schedule = _typed(component_id=wheel.id, service_type="Topup", interval_kind="period", interval_value=4, interval_unit="months")

    done = schedule_service.complete_schedule(schedule.id, today=TODAY)

    assert done.baseline_date == TODAY.isoformat()
    assert schedule_service.project_due_date(done, today=TODAY).is_overdue is False

