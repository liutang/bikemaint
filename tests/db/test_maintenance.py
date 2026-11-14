import pytest

from app.db import bikes as bikes_db
from app.db import connection
from app.db import maintenance as maintenance_db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as connection_:
        yield connection_


def _entry(conn, bike_id, performed_at, description="Service"):
    return maintenance_db.create(
        conn,
        bike_id=bike_id,
        component_id=None,
        description=description,
        performed_at=performed_at,
        mileage_at_service=0.0,
        schedule_id=None,
    )


def test_list_for_bike_is_latest_first_by_performed_at(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    _entry(conn, bike.id, "2026-03-01", "Third")
    _entry(conn, bike.id, "2026-01-01", "First")
    _entry(conn, bike.id, "2026-02-01", "Second")

    entries = maintenance_db.list_for_bike(conn, bike.id)

    assert [e.description for e in entries] == ["Third", "Second", "First"]


def test_list_for_bike_excludes_other_bikes_entries(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    other = bikes_db.create(conn, name="Gravel Bike")
    _entry(conn, bike.id, "2026-01-01", "Mine")
    _entry(conn, other.id, "2026-01-02", "Theirs")

    entries = maintenance_db.list_for_bike(conn, bike.id)

    assert [e.description for e in entries] == ["Mine"]


def test_update_and_delete_entry(conn):
    bike = bikes_db.create(conn, name="Road Bike")
    entry = _entry(conn, bike.id, "2026-01-01", "Old")

    updated = maintenance_db.update(
        conn, entry.id, description="New", performed_at="2026-01-05", mileage_at_service=12.5
    )
    assert (updated.description, updated.performed_at, updated.mileage_at_service) == (
        "New",
        "2026-01-05",
        12.5,
    )

    maintenance_db.delete(conn, entry.id)
    assert maintenance_db.get_by_id(conn, entry.id) is None
