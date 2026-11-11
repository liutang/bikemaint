import pytest

from app.db import connection
from app.services import bike_service, component_service, maintenance_service, sync_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def test_log_maintenance_captures_description_date_and_mileage_snapshot(db_path):
    bike = bike_service.create_bike(name="Road Bike", manual_baseline_mileage=120.0)

    entry = maintenance_service.log_maintenance(
        bike_id=bike.id, description="Lubed chain", performed_at="2026-05-01"
    )

    assert entry.description == "Lubed chain"
    assert entry.performed_at == "2026-05-01"
    assert entry.mileage_at_service == 120.0
    assert entry.bike_id == bike.id
    assert entry.component_id is None


def test_log_maintenance_allows_explicit_mileage_override(db_path):
    bike = bike_service.create_bike(name="Road Bike", manual_baseline_mileage=120.0)

    entry = maintenance_service.log_maintenance(
        bike_id=bike.id,
        description="Backdated service",
        performed_at="2026-05-01",
        mileage_at_service=90.0,
    )

    assert entry.mileage_at_service == 90.0


def test_log_maintenance_for_component_snapshots_component_mileage(db_path):
    component = component_service.create_component(
        name="Chain", component_type="chain", manual_baseline_mileage=300.0
    )

    entry = maintenance_service.log_maintenance(
        component_id=component.id, description="Cleaned", performed_at="2026-05-01"
    )

    assert entry.component_id == component.id
    assert entry.mileage_at_service == 300.0


def test_log_maintenance_requires_exactly_one_owner(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    component = component_service.create_component(name="Chain", component_type="chain")

    with pytest.raises(ValueError):
        maintenance_service.log_maintenance(description="x", performed_at="2026-05-01")
    with pytest.raises(ValueError):
        maintenance_service.log_maintenance(
            bike_id=bike.id,
            component_id=component.id,
            description="x",
            performed_at="2026-05-01",
        )


def test_log_maintenance_for_unknown_item_raises_lookup_error(db_path):
    with pytest.raises(LookupError):
        maintenance_service.log_maintenance(
            bike_id=999, description="x", performed_at="2026-05-01"
        )


def test_component_history_stays_with_component_after_moving_bikes(db_path):
    bike_a = bike_service.create_bike(name="Bike A")
    bike_b = bike_service.create_bike(name="Bike B")
    component = component_service.create_component(
        name="Chain", component_type="chain", parent_bike_id=bike_a.id
    )
    maintenance_service.log_maintenance(
        component_id=component.id, description="Waxed", performed_at="2026-05-01"
    )

    component_service.move_component(component.id, parent_bike_id=bike_b.id)

    history = maintenance_service.list_for_component(component.id)
    # the logged work stays with the part; moving it also records parts events
    assert [e.description for e in history if e.kind == "service"] == ["Waxed"]
    assert [e.description for e in maintenance_service.list_for_bike(bike_a.id) if e.kind == "service"] == []
    assert [e.description for e in maintenance_service.list_for_bike(bike_b.id) if e.kind == "service"] == []
    assert [e.description for e in history if e.kind == "event"] == [
        "Installed on Bike A", "Removed from Bike A", "Installed on Bike B",
    ]


def test_update_entry_changes_history(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    entry = maintenance_service.log_maintenance(
        bike_id=bike.id, description="Old", performed_at="2026-05-01"
    )

    maintenance_service.update_entry(
        entry.id, description="New", performed_at="2026-05-02", mileage_at_service=5.0
    )

    history = maintenance_service.list_for_bike(bike.id)
    assert [(e.description, e.performed_at, e.mileage_at_service) for e in history] == [
        ("New", "2026-05-02", 5.0)
    ]


def test_delete_entry_removes_it_from_history(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    entry = maintenance_service.log_maintenance(
        bike_id=bike.id, description="Oops", performed_at="2026-05-01"
    )

    maintenance_service.delete_entry(entry.id)

    assert maintenance_service.list_for_bike(bike.id) == []


def test_update_or_delete_unknown_entry_raises_lookup_error(db_path):
    with pytest.raises(LookupError):
        maintenance_service.update_entry(
            999, description="x", performed_at="2026-05-01", mileage_at_service=0.0
        )
    with pytest.raises(LookupError):
        maintenance_service.delete_entry(999)


def test_deleting_bike_with_maintenance_history_requires_confirmation(db_path):
    bike = bike_service.create_bike(name="Road Bike")
    maintenance_service.log_maintenance(
        bike_id=bike.id, description="Service", performed_at="2026-05-01"
    )

    with pytest.raises(bike_service.ConfirmationRequiredError):
        bike_service.delete_bike(bike.id)

    bike_service.delete_bike(bike.id, confirmed=True)
    assert bike_service.get_bike(bike.id) is None


def test_deleting_component_with_maintenance_history_requires_confirmation(db_path):
    component = component_service.create_component(name="Chain", component_type="chain")
    maintenance_service.log_maintenance(
        component_id=component.id, description="Waxed", performed_at="2026-05-01"
    )

    with pytest.raises(component_service.ConfirmationRequiredError):
        component_service.delete_component(component.id)

    component_service.delete_component(component.id, confirmed=True)
    assert component_service.get_component(component.id) is None
