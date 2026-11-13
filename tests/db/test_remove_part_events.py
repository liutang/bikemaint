"""Migration 0010 removes the automatic add/remove entries (specs/022-install-history-split, FR-002)."""

import shutil

from app.db import connection
from app.db.connection import MIGRATIONS_DIR


def test_migration_deletes_only_event_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    older = tmp_path / "migrations"
    older.mkdir()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name < "0010":
            shutil.copy(path, older / path.name)
    connection.run_migrations(older)  # the database as it was before this feature
    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO bike (name, bike_type, created_at, updated_at) VALUES ('B', 'road', 'x', 'x')"
        )
        for text, kind in (
            ("Added Chain (chain)", "event"),
            ("Removed Tire (tire)", "event"),
            ("Added a new cassette", "service"),  # logged by hand; starts like an event but is not one
            ("Waxed", "service"),
        ):
            conn.execute(
                "INSERT INTO maintenance_log_entry (bike_id, description, performed_at, mileage_at_service,"
                " kind, created_at, updated_at) VALUES (1, ?, '2026-01-01', 0, ?, 'x', 'x')",
                (text, kind),
            )

    connection.run_migrations()  # applies 0010

    with connection.get_connection() as conn:
        rows = [r["description"] for r in conn.execute(
            "SELECT description FROM maintenance_log_entry ORDER BY id")]
    assert rows == ["Added a new cassette", "Waxed"]
