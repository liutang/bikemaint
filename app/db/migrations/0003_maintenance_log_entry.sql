-- maintenance_log_entry: completed maintenance for a bike or component (FR-010).
-- Invariant (enforced in app/services/, not the DB): exactly one of bike_id /
-- component_id is non-NULL. schedule_id references maintenance_schedule, which is
-- created in a later migration; it stays NULL for free-standing entries.
CREATE TABLE maintenance_log_entry (
    id INTEGER PRIMARY KEY,
    bike_id INTEGER REFERENCES bike(id),
    component_id INTEGER REFERENCES component(id),
    description TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    mileage_at_service REAL NOT NULL,
    schedule_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_maintenance_log_entry_bike_id ON maintenance_log_entry(bike_id);
CREATE INDEX idx_maintenance_log_entry_component_id ON maintenance_log_entry(component_id);
