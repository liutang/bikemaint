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


# ------------------------------------------------ year/make/model bikes (specs/005, M1)


def test_create_from_details_derives_the_name_and_uses_the_category(db_path):
    bike = bike_service.create_bike_from_details(
        year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=12.5
    )

    assert bike.name == "2022 Trek Domane"
    assert (bike.year, bike.make, bike.model, bike.bike_type) == (2022, "Trek", "Domane", "road")
    assert bike.total_mileage == 12.5


def test_duplicate_names_get_a_numeric_suffix(db_path):
    names = [
        bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="road").name
        for _ in range(3)
    ]

    assert names == ["2022 Trek Domane", "2022 Trek Domane (2)", "2022 Trek Domane (3)"]


def test_deleted_bikes_do_not_count_towards_the_suffix(db_path):
    first = bike_service.create_bike_from_details(year=2020, make="Giant", model="TCR", category="road")
    bike_service.delete_bike(first.id)

    second = bike_service.create_bike_from_details(year=2020, make="Giant", model="TCR", category="road")

    assert second.name == "2020 Giant TCR"


def test_create_rejects_an_unknown_category(db_path):
    with pytest.raises(ValueError):
        bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="spaceship")
    assert bike_service.list_bikes() == []


def test_update_changes_the_details_and_renames(db_path):
    bike = bike_service.create_bike_from_details(
        year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=10
    )

    updated = bike_service.update_bike_from_details(
        bike.id, year=2023, make="Canyon", model="Grizl", category="gravel", manual_baseline_mileage=20
    )

    assert (updated.name, updated.bike_type) == ("2023 Canyon Grizl", "gravel")
    assert updated.manual_baseline_mileage == 20


def test_update_with_the_same_details_does_not_add_a_suffix(db_path):
    bike = bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="road")

    updated = bike_service.update_bike_from_details(
        bike.id, year=2022, make="Trek", model="Domane", category="gravel", manual_baseline_mileage=5
    )

    assert updated.name == "2022 Trek Domane" and updated.bike_type == "gravel"


def test_update_preserves_mileage_earned_beyond_the_baseline(db_path):
    bike = bike_service.create_bike_from_details(
        year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=10
    )
    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET total_mileage = 15.0 WHERE id = ?", (bike.id,))

    updated = bike_service.update_bike_from_details(
        bike.id, year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=20
    )

    assert updated.total_mileage == 25.0


def test_legacy_bike_can_keep_its_name_with_blank_details(db_path):
    bike = bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    updated = bike_service.update_bike_from_details(
        bike.id, year=None, make=None, model=None, category="other", manual_baseline_mileage=3
    )

    assert (updated.name, updated.bike_type, updated.manual_baseline_mileage) == ("Grandpa's Raleigh", "other", 3)
    assert updated.year is None


def test_legacy_bike_can_move_to_year_make_model(db_path):
    bike = bike_service.create_bike(name="Grandpa's Raleigh")

    updated = bike_service.update_bike_from_details(
        bike.id, year=1975, make="Raleigh", model="Competition", category="road", manual_baseline_mileage=0
    )

    assert updated.name == "1975 Raleigh Competition"


@pytest.mark.parametrize(
    "details",
    [
        {"year": 2020, "make": None, "model": None},
        {"year": None, "make": "Trek", "model": None},
        {"year": 2020, "make": "Trek", "model": ""},
    ],
)
def test_a_mix_of_filled_and_blank_details_is_refused(db_path, details):
    bike = bike_service.create_bike(name="Grandpa's Raleigh")

    with pytest.raises(ValueError):
        bike_service.update_bike_from_details(bike.id, category="road", manual_baseline_mileage=0, **details)
    assert bike_service.get_bike(bike.id).name == "Grandpa's Raleigh"


def test_a_bike_with_details_cannot_blank_them(db_path):
    bike = bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="road")

    with pytest.raises(ValueError):
        bike_service.update_bike_from_details(
            bike.id, year=None, make=None, model=None, category="road", manual_baseline_mileage=0
        )


def test_update_for_a_missing_bike_raises_lookup_error(db_path):
    with pytest.raises(LookupError):
        bike_service.update_bike_from_details(
            999, year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=0
        )
