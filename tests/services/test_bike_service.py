import pytest

from app.db import connection
from app.services import bike_service, component_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_create_bike_starts_with_zero_mileage_by_default(db_path):
    bike = bike_service.create_bike(name="Gravel Rig")

    assert bike.name == "Gravel Rig"
    assert bike.manual_baseline_mileage == 0
    assert bike.total_mileage == 0
    assert bike.is_deleted is False


def test_create_bike_with_baseline_mileage_starts_total_at_baseline(db_path):
    bike = bike_service.create_bike(name="Road Bike", manual_baseline_mileage=250.5)

    assert bike.total_mileage == 250.5


def test_update_bike_preserves_mileage_earned_beyond_the_baseline(db_path):
    bike = bike_service.create_bike(name="Road Bike", manual_baseline_mileage=10.0)

    # Simulate mileage accrued since creation (e.g. a future Strava sync).
    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET total_mileage = 15.0 WHERE id = ?", (bike.id,))

    updated = bike_service.update_bike(
        bike.id, name="Road Bike (renamed)", bike_type="road", manual_baseline_mileage=20.0
    )

    assert updated.name == "Road Bike (renamed)"
    assert updated.bike_type == "road"
    assert updated.manual_baseline_mileage == 20.0
    # 5 miles earned beyond the old baseline is preserved on top of the new baseline.
    assert updated.total_mileage == 25.0


def test_delete_bike_with_no_components_soft_deletes_immediately(db_path):
    bike = bike_service.create_bike(name="Spare Frame")

    bike_service.delete_bike(bike.id)

    with connection.get_connection() as conn:
        row = conn.execute("SELECT is_deleted FROM bike WHERE id = ?", (bike.id,)).fetchone()
    assert row["is_deleted"] == 1


def test_delete_bike_with_installed_components_requires_confirmation(db_path):
    bike = bike_service.create_bike(name="Commuter")
    component_service.create_component(
        name="Front Wheel", component_type="wheel", parent_bike_id=bike.id
    )

    with pytest.raises(bike_service.ConfirmationRequiredError):
        bike_service.delete_bike(bike.id)

    with connection.get_connection() as conn:
        row = conn.execute("SELECT is_deleted FROM bike WHERE id = ?", (bike.id,)).fetchone()
    assert row["is_deleted"] == 0


def test_delete_bike_confirmed_cascades_to_installed_components(db_path):
    bike = bike_service.create_bike(name="Commuter")
    wheel = component_service.create_component(
        name="Front Wheel", component_type="wheel", parent_bike_id=bike.id
    )

    bike_service.delete_bike(bike.id, confirmed=True)

    with connection.get_connection() as conn:
        bike_row = conn.execute("SELECT is_deleted FROM bike WHERE id = ?", (bike.id,)).fetchone()
        component_row = conn.execute(
            "SELECT is_deleted FROM component WHERE id = ?", (wheel.id,)
        ).fetchone()
    assert bike_row["is_deleted"] == 1
    assert component_row["is_deleted"] == 1
