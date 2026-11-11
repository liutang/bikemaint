import pytest

from app.db import bikes, components, connection


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_get_tree_for_bike_returns_arbitrary_depth_nesting(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Gravel Bike")
        wheel = components.create(
            conn, name="Wheel", component_type="wheel", parent_bike_id=bike.id
        )
        rim = components.create(
            conn, name="Rim", component_type="rim", parent_component_id=wheel.id
        )
        tire = components.create(
            conn, name="Tire", component_type="tire", parent_component_id=rim.id
        )
        # An unrelated bike's component must not leak into the tree.
        other_bike = bikes.create(conn, name="Other Bike")
        components.create(
            conn, name="Other Wheel", component_type="wheel", parent_bike_id=other_bike.id
        )

        tree = components.get_tree_for_bike(conn, bike.id)

    tree_ids = {component.id for component in tree}
    assert tree_ids == {wheel.id, rim.id, tire.id}


def test_get_descendants_excludes_the_root_and_unrelated_branches(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Gravel Bike")
        wheel = components.create(
            conn, name="Wheel", component_type="wheel", parent_bike_id=bike.id
        )
        rim = components.create(
            conn, name="Rim", component_type="rim", parent_component_id=wheel.id
        )
        tire = components.create(
            conn, name="Tire", component_type="tire", parent_component_id=rim.id
        )
        sibling = components.create(
            conn, name="Hub", component_type="hub", parent_component_id=wheel.id
        )

        descendants = components.get_descendants(conn, wheel.id)

    descendant_ids = {component.id for component in descendants}
    assert descendant_ids == {rim.id, tire.id, sibling.id}
    assert wheel.id not in descendant_ids


def test_get_descendants_of_a_leaf_is_empty(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Gravel Bike")
        wheel = components.create(
            conn, name="Wheel", component_type="wheel", parent_bike_id=bike.id
        )

        descendants = components.get_descendants(conn, wheel.id)

    assert descendants == []


def test_resolve_top_bike_id_walks_up_nested_parents(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Gravel Bike")
        wheel = components.create(
            conn, name="Wheel", component_type="wheel", parent_bike_id=bike.id
        )
        rim = components.create(
            conn, name="Rim", component_type="rim", parent_component_id=wheel.id
        )

        top_bike_id = components.resolve_top_bike_id(conn, rim.id)

    assert top_bike_id == bike.id


def test_resolve_top_bike_id_returns_none_for_a_subassembly_in_storage(db_path):
    with connection.get_connection() as conn:
        wheel = components.create(conn, name="Wheel", component_type="wheel")
        rim = components.create(
            conn, name="Rim", component_type="rim", parent_component_id=wheel.id
        )

        top_bike_id = components.resolve_top_bike_id(conn, rim.id)

    assert top_bike_id is None
