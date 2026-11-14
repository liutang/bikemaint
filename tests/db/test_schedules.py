import pytest

from app.db import bikes as bikes_db
from app.db import connection
from app.db import notifications as notifications_db
from app.db import schedules as schedules_db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as connection_:
        yield connection_


def _schedule(conn, bike_id, name="Service"):
    return schedules_db.create(
        conn,
        bike_id=bike_id,
        component_id=None,
        name=name,
        interval_miles=100.0,
        interval_days=None,
        baseline_mileage=10.0,
        baseline_date="2026-01-01",
    )


def test_create_defaults_to_cycle_one_and_active(conn):
    bike = bikes_db.create(conn, name="Road Bike")

    schedule = _schedule(conn, bike.id)

    assert schedule.cycle_number == 1
    assert schedule.is_active is True
    assert schedule.interval_miles == 100.0
    assert schedule.interval_days is None


def test_complete_bumps_cycle_and_resets_baseline(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    schedule = _schedule(conn, bike.id)

    completed = schedules_db.complete(
        conn, schedule.id, baseline_mileage=250.0, baseline_date="2026-06-01"
    )

    assert completed.cycle_number == 2
    assert completed.baseline_mileage == 250.0
    assert completed.baseline_date == "2026-06-01"


def test_deactivated_schedules_are_excluded_from_active_listings(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    kept = _schedule(conn, bike.id, "Kept")
    gone = _schedule(conn, bike.id, "Gone")

    schedules_db.deactivate(conn, gone.id)

    assert [s.id for s in schedules_db.list_active_for_bike(conn, bike.id)] == [kept.id]
    assert [s.id for s in schedules_db.list_all_active(conn)] == [kept.id]
    assert schedules_db.get_by_id(conn, gone.id) is not None


def test_notification_unique_per_schedule_and_cycle(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    schedule = _schedule(conn, bike.id)

    first = notifications_db.insert(
        conn, schedule_id=schedule.id, cycle_number=1, projected_due_at="2026-10-02"
    )
    duplicate = notifications_db.insert(
        conn, schedule_id=schedule.id, cycle_number=1, projected_due_at="2026-10-05"
    )
    next_cycle = notifications_db.insert(
        conn, schedule_id=schedule.id, cycle_number=2, projected_due_at="2026-12-01"
    )

    assert first is not None
    assert duplicate is None
    assert next_cycle is not None


def test_acknowledge_and_webhook_result_are_recorded(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    schedule = _schedule(conn, bike.id)
    notification = notifications_db.insert(
        conn, schedule_id=schedule.id, cycle_number=1, projected_due_at="2026-10-02"
    )

    notifications_db.record_webhook_result(
        conn, notification.id, delivered=False, error="HTTP 500"
    )
    assert notifications_db.list_unacknowledged(conn)[0].webhook_delivery_error == "HTTP 500"

    notifications_db.mark_acknowledged(conn, notification.id)
    assert notifications_db.list_unacknowledged(conn) == []


def test_a_typed_schedule_round_trips_its_new_fields(conn):
    bike = bikes_db.create(conn, name="Road Bike")

    schedule = schedules_db.create(
        conn, bike_id=bike.id, component_id=None, name="Check", interval_miles=None, interval_days=None,
        baseline_mileage=0.0, baseline_date="2026-01-01", service_type="Check", interval_kind="usage",
        interval_value=50.0, interval_unit="rides", is_recurring=False, notify=False,
        baseline_at="2026-01-01T09:00:00.000000Z",
    )

    got = schedules_db.get_by_id(conn, schedule.id)
    assert (got.service_type, got.interval_kind, got.interval_value, got.interval_unit) == ("Check", "usage", 50.0, "rides")
    assert (got.is_recurring, got.notify, got.baseline_at) == (False, False, "2026-01-01T09:00:00.000000Z")


def test_old_style_schedules_default_to_recurring_with_notifications(conn):
    bike = bikes_db.create(conn, name="Road Bike")

    schedule = _schedule(conn, bike.id)

    assert (schedule.is_recurring, schedule.notify, schedule.service_type, schedule.interval_kind) == (True, True, None, None)


def test_update_typed_converts_an_old_schedule_and_keeps_its_cycle(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    schedule = _schedule(conn, bike.id)

    converted = schedules_db.update_typed(
        conn, schedule.id, name="Replace", service_type="Replace", interval_miles=None, interval_days=14,
        interval_kind="period", interval_value=2.0, interval_unit="weeks", is_recurring=True, notify=False,
        is_active=True,
    )

    assert (converted.name, converted.service_type, converted.interval_days, converted.interval_miles) == ("Replace", "Replace", 14, None)
    assert (converted.interval_unit, converted.notify, converted.cycle_number, converted.baseline_mileage) == ("weeks", False, 1, 10.0)


def test_complete_can_record_the_baseline_moment(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    schedule = _schedule(conn, bike.id)

    completed = schedules_db.complete(
        conn, schedule.id, baseline_mileage=1.0, baseline_date="2026-06-01", baseline_at="2026-06-01T10:00:00.000000Z"
    )

    assert completed.baseline_at == "2026-06-01T10:00:00.000000Z"
