"""Sibling order for components (specs/004-bike-builder, M3, FR-013)."""

import sqlite3

import pytest

from app.db import bikes, components, connection


@pytest.fixture
def conn(db_path):
    connection.run_migrations()
    with connection.get_connection() as c:
        yield c


def _bike(conn):
    return bikes.create(conn, name="Bike")


def _names(rows):
    return [c.name for c in rows]


def test_new_children_are_appended_in_creation_order(conn):
    bike = _bike(conn)
    for name in ("A", "B", "C"):
        components.create(conn, name=name, component_type="bolt", parent_bike_id=bike.id)

    kids = components.list_children(conn, parent_bike_id=bike.id)

    assert _names(kids) == ["A", "B", "C"]
    assert [c.position for c in kids] == [0, 1, 2]


def test_positions_are_per_parent(conn):
    bike = _bike(conn)
    wheel = components.create(conn, name="W", component_type="wheel", parent_bike_id=bike.id)
    components.create(conn, name="S1", component_type="spoke", parent_component_id=wheel.id)
    spare = components.create(conn, name="Spare", component_type="tire")

    assert components.list_children(conn, parent_component_id=wheel.id)[0].position == 0
    assert spare.position == 0


def test_reorder_before_a_sibling(conn):
    bike = _bike(conn)
    a, b, c = (
        components.create(conn, name=n, component_type="bolt", parent_bike_id=bike.id) for n in "ABC"
    )

    components.reorder(conn, c.id, before_component_id=a.id)

    assert _names(components.list_children(conn, parent_bike_id=bike.id)) == ["C", "A", "B"]
    assert [x.position for x in components.list_children(conn, parent_bike_id=bike.id)] == [0, 1, 2]


def test_reorder_to_the_end(conn):
    bike = _bike(conn)
    a, b, c = (
        components.create(conn, name=n, component_type="bolt", parent_bike_id=bike.id) for n in "ABC"
    )

    components.reorder(conn, a.id, before_component_id=None)

    assert _names(components.list_children(conn, parent_bike_id=bike.id)) == ["B", "C", "A"]


def test_reorder_in_place_changes_nothing(conn):
    bike = _bike(conn)
    a, b = (
        components.create(conn, name=n, component_type="bolt", parent_bike_id=bike.id) for n in "AB"
    )

    components.reorder(conn, a.id, before_component_id=b.id)

    assert _names(components.list_children(conn, parent_bike_id=bike.id)) == ["A", "B"]


def test_reorder_rejects_a_target_that_is_not_a_sibling(conn):
    bike = _bike(conn)
    a = components.create(conn, name="A", component_type="bolt", parent_bike_id=bike.id)
    stranger = components.create(conn, name="X", component_type="bolt")

    with pytest.raises(ValueError):
        components.reorder(conn, a.id, before_component_id=stranger.id)
    with pytest.raises(ValueError):
        components.reorder(conn, a.id, before_component_id=a.id)


def test_set_parent_appends_to_the_new_parents_end(conn):
    bike = _bike(conn)
    other = bikes.create(conn, name="Other")
    components.create(conn, name="A", component_type="bolt", parent_bike_id=other.id)
    mover = components.create(conn, name="M", component_type="bolt", parent_bike_id=bike.id)

    moved = components.set_parent(conn, mover.id, parent_bike_id=other.id, parent_component_id=None)

    assert moved.position == 1
    assert _names(components.list_children(conn, parent_bike_id=other.id)) == ["A", "M"]


def test_tree_and_descendant_reads_use_position_order(conn):
    bike = _bike(conn)
    wheel = components.create(conn, name="W", component_type="wheel", parent_bike_id=bike.id)
    s1, s2 = (
        components.create(conn, name=n, component_type="spoke", parent_component_id=wheel.id)
        for n in ("S1", "S2")
    )
    components.reorder(conn, s2.id, before_component_id=s1.id)

    assert _names(components.get_descendants(conn, wheel.id)) == ["S2", "S1"]
    tree = components.get_tree_for_bike(conn, bike.id)
    assert _names([c for c in tree if c.parent_component_id == wheel.id]) == ["S2", "S1"]


def test_deleted_siblings_do_not_count(conn):
    bike = _bike(conn)
    a = components.create(conn, name="A", component_type="bolt", parent_bike_id=bike.id)
    components.soft_delete(conn, a.id)
    b = components.create(conn, name="B", component_type="bolt", parent_bike_id=bike.id)

    assert b.position == 0


def test_migration_backfills_existing_rows_in_id_order(db_path):
    # Build a database at schema version 5, insert rows, then apply migration 6.
    raw = sqlite3.connect(db_path)
    raw.row_factory = sqlite3.Row
    from app.db.connection import MIGRATIONS_DIR

    for path in sorted(MIGRATIONS_DIR.glob("000[1-5]_*.sql")):
        raw.executescript(path.read_text())
    raw.execute("INSERT INTO bike (name, created_at, updated_at) VALUES ('B', 'x', 'x')")
    for name in ("A", "B", "C"):
        raw.execute(
            "INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at)"
            " VALUES (?, 'bolt', 1, 'x', 'x')",
            (name,),
        )
    raw.execute(
        "INSERT INTO component (name, component_type, created_at, updated_at)"
        " VALUES ('Stored', 'tire', 'x', 'x')"
    )
    raw.executescript((MIGRATIONS_DIR / "0006_component_position.sql").read_text())

    rows = raw.execute("SELECT name, position FROM component ORDER BY id").fetchall()

    assert [(r["name"], r["position"]) for r in rows] == [("A", 0), ("B", 1), ("C", 2), ("Stored", 0)]
