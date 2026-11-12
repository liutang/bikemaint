"""Installation-period queries (specs/015)."""

import pytest

from app.db import components as components_db, connection


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as c:
        c.execute("INSERT INTO bike (name, created_at, updated_at) VALUES ('A', 'x', 'x')")
        yield c


def _part(conn):
    return components_db.create(
        conn, name="S", component_type="saddle", parent_bike_id=None, parent_component_id=None,
        manual_baseline_mileage=0,
    ).id


def _p(conn, cid, a, b):
    return components_db.insert_period(
        conn, cid, parent_bike_id=1, parent_component_id=None,
        installed_at=f"{a}T00:00:00.000000Z", removed_at=f"{b}T00:00:00.000000Z" if b else None,
    )


def test_insert_list_update_delete(conn):
    cid = _part(conn)
    p = _p(conn, cid, "2025-01-01", "2025-02-01")
    assert [x.id for x in components_db.list_periods(conn, cid)] == [p.id]
    updated = components_db.update_period(
        conn, p.id, parent_bike_id=1, parent_component_id=None,
        installed_at="2025-01-05T00:00:00.000000Z", removed_at="2025-02-05T00:00:00.000000Z",
    )
    assert updated.installed_at.startswith("2025-01-05")
    components_db.delete_period(conn, p.id)
    assert components_db.get_period(conn, p.id) is None


def test_overlap_detection_ignores_touching_and_excluded(conn):
    cid = _part(conn)
    p = _p(conn, cid, "2025-01-01", "2025-02-01")
    find = lambda a, b, ex=None: components_db.find_overlapping_period(  # noqa: E731
        conn, cid, installed_at=f"{a}T00:00:00.000000Z",
        removed_at=f"{b}T00:00:00.000000Z" if b else None, exclude_period_id=ex,
    )
    assert find("2025-01-15", "2025-03-01").id == p.id
    assert find("2025-02-01", "2025-03-01") is None
    assert find("2024-12-01", "2025-01-01") is None
    assert find("2025-01-15", None).id == p.id
    assert find("2025-01-15", "2025-01-20", ex=p.id) is None
