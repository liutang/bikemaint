"""The palette is grouped into categories (specs/020-free-placement-and-categories, US2)."""

import pytest

from app.db import connection
from app.models import component_kinds
from app.services import bike_service, builder_service, component_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_the_palette_groups_every_offered_part_by_category_in_order(db_path):
    bike = bike_service.create_bike(name="Road")

    view = builder_service.build_view(bike.id)

    assert [c.name for c in view.palette] == list(component_kinds.CATEGORIES)
    flat = [(c.name, i.type, i.label) for c in view.palette for i in c.items]
    expected = [(cat, k.type, k.name) for cat, kinds in component_kinds.offered_by_category() for k in kinds]
    assert flat == expected and len(flat) == 34


def test_every_screen_lists_the_whole_palette_with_every_slot_as_a_target(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)

    on_wheel = builder_service.build_view(f"component:{wheel.id}")

    items = [i for c in on_wheel.palette for i in c.items]
    assert len(items) == 34
    assert all([t.value for t in i.targets] == [f"component:{wheel.id}"] for i in items)
