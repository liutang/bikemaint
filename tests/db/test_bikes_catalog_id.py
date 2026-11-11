"""`bike.catalog_id` ties a bike to its catalog entry (specs/004-bike-builder, M1)."""

import pytest

from app.db import bikes, connection


@pytest.fixture
def migrated(db_path):
    connection.run_migrations()


def test_new_bikes_can_store_a_catalog_id(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Trek Domane", bike_type="road", catalog_id="trek-domane")

        assert bike.catalog_id == "trek-domane"
        assert bikes.get_by_id(conn, bike.id).catalog_id == "trek-domane"


def test_legacy_style_bikes_have_no_catalog_id(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="My old bike")

        assert bike.catalog_id is None


def test_update_can_set_and_keep_the_catalog_id(migrated):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="My old bike")

        updated = bikes.update(
            conn, bike.id, name="Giant TCR", bike_type="road",
            manual_baseline_mileage=0, total_mileage=0, catalog_id="giant-tcr",
        )

        assert (updated.name, updated.catalog_id) == ("Giant TCR", "giant-tcr")


def test_migration_is_idempotent_and_keeps_existing_rows(db_path):
    connection.run_migrations()
    with connection.get_connection() as conn:
        bikes.create(conn, name="Existing")
    connection.run_migrations()  # second run must not fail or lose data
    with connection.get_connection() as conn:
        assert [b.name for b in bikes.list_active(conn)] == ["Existing"]
