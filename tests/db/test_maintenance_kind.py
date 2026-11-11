"""Maintenance entries gain a kind and an optional time (specs/006, M2)."""

import pytest

from app.db import bikes, connection, maintenance


@pytest.fixture
def conn(db_path):
    connection.run_migrations()
    with connection.get_connection() as c:
        yield c


def _entry(conn, bike_id, **kw):
    return maintenance.create(
        conn, bike_id=bike_id, component_id=None, description=kw.pop("description", "x"),
        performed_at=kw.pop("performed_at", "2026-05-01"), mileage_at_service=0, **kw,
    )


def test_entries_default_to_service_kind_without_a_time(conn):
    bike = bikes.create(conn, name="B")

    entry = _entry(conn, bike.id)

    assert (entry.kind, entry.performed_time) == ("service", None)


def test_event_entries_and_typed_times_round_trip(conn):
    bike = bikes.create(conn, name="B")

    event = _entry(conn, bike.id, kind="event", description="Added Chain (chain)")
    timed = _entry(conn, bike.id, performed_time="14:30")

    assert maintenance.get_by_id(conn, event.id).kind == "event"
    assert maintenance.get_by_id(conn, timed.id).performed_time == "14:30"


def test_events_do_not_count_as_maintenance_history(conn):
    bike = bikes.create(conn, name="B")
    _entry(conn, bike.id, kind="event")

    assert maintenance.has_entries_for_bike(conn, bike.id) is False

    _entry(conn, bike.id)  # a real service entry
    assert maintenance.has_entries_for_bike(conn, bike.id) is True


def test_events_do_not_count_for_components_either(conn):
    from app.db import components

    part = components.create(conn, name="C", component_type="chain")
    maintenance.create(conn, bike_id=None, component_id=part.id, description="x", performed_at="2026-05-01",
                       mileage_at_service=0, kind="event")

    assert maintenance.has_entries_for_component(conn, part.id) is False


def test_entries_sort_by_date_then_time(conn):
    bike = bikes.create(conn, name="B")
    late = _entry(conn, bike.id, performed_at="2026-05-01", performed_time="18:00", description="late")
    early = _entry(conn, bike.id, performed_at="2026-05-01", performed_time="08:00", description="early")
    next_day = _entry(conn, bike.id, performed_at="2026-05-02", description="next day")

    assert [e.description for e in maintenance.list_for_bike(conn, bike.id)] == ["early", "late", "next day"]
    assert late.id and early.id and next_day.id


def test_update_keeps_kind_and_can_set_the_time(conn):
    bike = bikes.create(conn, name="B")
    event = _entry(conn, bike.id, kind="event")

    updated = maintenance.update(conn, event.id, description="d", performed_at="2026-05-03",
                                 mileage_at_service=1, performed_time="09:15")

    assert (updated.kind, updated.performed_time) == ("event", "09:15")
