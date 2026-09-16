import pytest

from app.db import connection
from app.models import rows


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return path


def test_account_from_row_maps_every_column(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO account (
                strava_athlete_id, strava_access_token, strava_refresh_token,
                strava_token_expires_at, strava_connected_at, strava_connection_stale,
                notification_webhook_url, notification_lead_time_days,
                created_at, updated_at
            ) VALUES (1, 'access', 'refresh', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 1,
                      'https://example.com/hook', 14, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        )
        row = conn.execute("SELECT * FROM account").fetchone()

    account = rows.Account.from_row(row)

    assert account == rows.Account(
        id=account.id,
        strava_athlete_id=1,
        strava_access_token="access",
        strava_refresh_token="refresh",
        strava_token_expires_at="2026-01-01T00:00:00Z",
        strava_connected_at="2026-01-01T00:00:00Z",
        strava_connection_stale=True,
        notification_webhook_url="https://example.com/hook",
        notification_lead_time_days=14,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_bike_from_row_maps_nullable_columns(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO bike (name, created_at, updated_at)
            VALUES ('Gravel Bike', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        )
        row = conn.execute("SELECT * FROM bike").fetchone()

    bike = rows.Bike.from_row(row)

    assert bike.name == "Gravel Bike"
    assert bike.bike_type is None
    assert bike.strava_gear_id is None
    assert bike.strava_paired_at is None
    assert bike.manual_baseline_mileage == 0
    assert bike.total_mileage == 0
    assert bike.is_deleted is False


def test_component_from_row_maps_parent_columns(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO bike (name, created_at, updated_at) VALUES ('Gravel Bike', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )
        bike_id = conn.execute("SELECT id FROM bike").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at)
            VALUES ('Front Wheel', 'wheel', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """,
            (bike_id,),
        )
        row = conn.execute("SELECT * FROM component").fetchone()

    component = rows.Component.from_row(row)

    assert component.component_type == "wheel"
    assert component.parent_bike_id == bike_id
    assert component.parent_component_id is None
    assert component.is_deleted is False


def test_component_installation_period_from_row(db_path):
    connection.run_migrations()

    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO bike (name, created_at, updated_at) VALUES ('Gravel Bike', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )
        bike_id = conn.execute("SELECT id FROM bike").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO component (name, component_type, parent_bike_id, created_at, updated_at)
            VALUES ('Front Wheel', 'wheel', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """,
            (bike_id,),
        )
        component_id = conn.execute("SELECT id FROM component").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO component_installation_period (component_id, parent_bike_id, installed_at)
            VALUES (?, ?, '2026-01-01T00:00:00Z')
            """,
            (component_id, bike_id),
        )
        row = conn.execute("SELECT * FROM component_installation_period").fetchone()

    period = rows.ComponentInstallationPeriod.from_row(row)

    assert period.component_id == component_id
    assert period.parent_bike_id == bike_id
    assert period.parent_component_id is None
    assert period.removed_at is None
