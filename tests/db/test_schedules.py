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
