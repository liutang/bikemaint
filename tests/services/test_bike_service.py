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


def test_unpaired_gear_excludes_gear_already_paired_to_a_bike(tmp_path, monkeypatch):
    from app.db import connection

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    connection.run_migrations()
    bike = bike_service.create_bike(name="Paired Bike")
    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET strava_gear_id = 'g1' WHERE id = ?", (bike.id,))

    gear = [{"id": "g1", "name": "Taken"}, {"id": "g2", "name": "Free"}]

    assert bike_service.unpaired_gear(gear) == [{"id": "g2", "name": "Free"}]


# ------------------------------------------------ catalog bikes (specs/004-bike-builder, M1)


def test_create_from_catalog_names_the_bike_and_derives_its_type(db_path):
    bike = bike_service.create_bike_from_catalog("trek-domane", manual_baseline_mileage=12.5)

    assert bike.name == "Trek Domane"
    assert bike.bike_type == "road"
    assert bike.catalog_id == "trek-domane"
    assert bike.total_mileage == 12.5


def test_duplicate_catalog_bikes_get_a_numeric_suffix(db_path):
    names = [bike_service.create_bike_from_catalog("trek-domane").name for _ in range(3)]

    assert names == ["Trek Domane", "Trek Domane (2)", "Trek Domane (3)"]


def test_deleted_bikes_do_not_count_towards_the_suffix(db_path):
    first = bike_service.create_bike_from_catalog("giant-tcr")
    bike_service.delete_bike(first.id)

    assert bike_service.create_bike_from_catalog("giant-tcr").name == "Giant TCR"


def test_a_legacy_bike_named_like_a_catalog_entry_also_forces_a_suffix(db_path):
    bike_service.create_bike(name="Trek Domane")

    assert bike_service.create_bike_from_catalog("trek-domane").name == "Trek Domane (2)"


@pytest.mark.parametrize("bad", ["", "nope", "__keep__", None, "trek-domane'; --"])
def test_create_from_catalog_rejects_unknown_ids(db_path, bad):
    with pytest.raises(ValueError):
        bike_service.create_bike_from_catalog(bad)
    assert bike_service.list_bikes() == []


def test_update_to_a_different_catalog_entry_renames_and_retypes(db_path):
    bike = bike_service.create_bike_from_catalog("trek-domane", manual_baseline_mileage=10)

    updated = bike_service.update_bike_from_catalog(
        bike.id, "canyon-grizl", manual_baseline_mileage=20
    )

    assert (updated.name, updated.bike_type, updated.catalog_id) == ("Canyon Grizl", "gravel", "canyon-grizl")
    assert updated.manual_baseline_mileage == 20


def test_update_keeping_the_same_catalog_entry_does_not_add_a_suffix(db_path):
    bike = bike_service.create_bike_from_catalog("trek-domane")

    updated = bike_service.update_bike_from_catalog(bike.id, "trek-domane", manual_baseline_mileage=5)

    assert updated.name == "Trek Domane"
    assert updated.manual_baseline_mileage == 5


def test_legacy_bike_can_keep_its_current_name_and_type(db_path):
    bike = bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    updated = bike_service.update_bike_from_catalog(
        bike.id, bike_service.KEEP_CURRENT, manual_baseline_mileage=3
    )

    assert (updated.name, updated.bike_type, updated.catalog_id) == ("Grandpa's Raleigh", "vintage", None)
    assert updated.manual_baseline_mileage == 3


def test_legacy_bike_can_move_to_a_catalog_entry(db_path):
    bike = bike_service.create_bike(name="Grandpa's Raleigh")

    updated = bike_service.update_bike_from_catalog(bike.id, "specialized-sirrus", manual_baseline_mileage=0)

    assert (updated.name, updated.catalog_id) == ("Specialized Sirrus", "specialized-sirrus")


def test_keep_current_is_refused_for_bikes_created_from_the_catalog(db_path):
    bike = bike_service.create_bike_from_catalog("trek-domane")

    with pytest.raises(ValueError):
        bike_service.update_bike_from_catalog(bike.id, bike_service.KEEP_CURRENT, manual_baseline_mileage=0)


def test_update_from_catalog_for_a_missing_bike_raises_lookup_error(db_path):
    with pytest.raises(LookupError):
        bike_service.update_bike_from_catalog(999, "trek-domane", manual_baseline_mileage=0)
