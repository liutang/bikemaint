"""`bike.year/make/model` describe a bike (specs/005-unified-bike-screen, M1)."""

import pytest

from app.db import bikes, connection


@pytest.fixture
def migrated(db_path):
    connection.run_migrations()


def test_bikes_store_year_make_and_model(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(
            conn, name="2022 Trek Domane", bike_type="road", year=2022, make="Trek", model="Domane"
        )

        loaded = bikes.get_by_id(conn, bike.id)

    assert (loaded.year, loaded.make, loaded.model) == (2022, "Trek", "Domane")


def test_legacy_bikes_have_no_year_make_or_model(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="My old bike")

    assert (bike.year, bike.make, bike.model) == (None, None, None)


def test_update_sets_and_clears_the_details(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="My old bike")

        updated = bikes.update(
            conn, bike.id, name="2020 Giant TCR", bike_type="road", manual_baseline_mileage=0,
            total_mileage=0, year=2020, make="Giant", model="TCR",
        )

    assert (updated.name, updated.year, updated.make, updated.model) == ("2020 Giant TCR", 2020, "Giant", "TCR")


def test_the_catalog_column_is_gone_and_migration_is_idempotent(migrated):
    connection.run_migrations()
    with connection.get_connection() as conn:
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(bike)")]
    assert "catalog_id" not in columns
    assert {"year", "make", "model"} <= set(columns)


def test_existing_rows_survive_the_migration(db_path):
    import sqlite3

    from app.db.connection import MIGRATIONS_DIR

    raw = sqlite3.connect(db_path)
    for path in sorted(MIGRATIONS_DIR.glob("000[1-6]_*.sql")):
        raw.executescript(path.read_text())
    raw.execute(
        "INSERT INTO bike (name, bike_type, catalog_id, created_at, updated_at) "
        "VALUES ('Trek Domane', 'road', 'trek-domane', 'x', 'x')"
    )
    raw.executescript((MIGRATIONS_DIR / "0007_bike_year_make_model.sql").read_text())

    row = raw.execute("SELECT name, bike_type, year, make, model FROM bike").fetchone()

    assert row == ("Trek Domane", "road", None, None, None)
