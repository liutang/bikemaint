"""Archived state and the archived-tree query (specs/079 data-model.md)."""

import pytest

from app.db import bikes, components, connection

AT = "2026-11-18T15:00:00.000000Z"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def test_bikes_and_parts_start_active_and_can_be_archived_and_back(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Madone")
        part = components.create(conn, name="Chain", component_type="chain")
        assert bike.archived_at is None and part.archived_at is None
        bikes.set_archived(conn, bike.id, AT)
        components.set_archived(conn, part.id, AT)
        assert bikes.get_by_id(conn, bike.id).archived_at == AT
        assert components.get_by_id(conn, part.id).archived_at == AT
        bikes.set_archived(conn, bike.id, None)
        assert bikes.get_by_id(conn, bike.id).archived_at is None


def test_list_archived_bikes_lists_only_archived_ones_newest_first(db_path):
    with connection.get_connection() as conn:
        old, new, active = (bikes.create(conn, name=n) for n in ("Old", "New", "Active"))
        bikes.set_archived(conn, old.id, "2025-01-01T00:00:00.000000Z")
        bikes.set_archived(conn, new.id, AT)
        assert [b.name for b in bikes.list_archived(conn)] == ["New", "Old"]
        assert [c.name for c in components.list_archived(conn)] == []


def test_a_part_is_in_an_archived_tree_when_it_its_parents_or_its_bike_is_archived(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Madone")
        wheel = components.create(conn, name="Wheel", component_type="wheel", parent_bike_id=bike.id)
        tire = components.create(conn, name="Tire", component_type="tire", parent_component_id=wheel.id)
        tube = components.create(conn, name="Tube", component_type="tube", parent_component_id=tire.id)
        spare = components.create(conn, name="Spare", component_type="chain")
        assert not any(components.is_in_archived_tree(conn, p.id) for p in (wheel, tire, tube, spare))

        bikes.set_archived(conn, bike.id, AT)
        assert all(components.is_in_archived_tree(conn, p.id) for p in (wheel, tire, tube))
        assert not components.is_in_archived_tree(conn, spare.id)

        bikes.set_archived(conn, bike.id, None)
        components.set_archived(conn, tire.id, AT)
        assert components.is_in_archived_tree(conn, tire.id) and components.is_in_archived_tree(conn, tube.id)
        assert not components.is_in_archived_tree(conn, wheel.id)
