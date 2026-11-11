-- maintenance_schedule: a recurring maintenance definition for a bike or component (FR-013).
-- Invariant (enforced in app/services/, not the DB): exactly one of bike_id / component_id
-- is non-NULL. The projected due date is computed on read, never stored (research.md §4).
CREATE TABLE maintenance_schedule (
    id INTEGER PRIMARY KEY,
    bike_id INTEGER REFERENCES bike(id),
    component_id INTEGER REFERENCES component(id),
    name TEXT NOT NULL,
    interval_miles REAL,
    interval_days INTEGER,
    baseline_mileage REAL NOT NULL,
    baseline_date TEXT NOT NULL,
    cycle_number INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (interval_miles IS NOT NULL OR interval_days IS NOT NULL)
);

CREATE INDEX idx_maintenance_schedule_bike_id ON maintenance_schedule(bike_id);
CREATE INDEX idx_maintenance_schedule_component_id ON maintenance_schedule(component_id);

-- notification: a recorded due-soon alert. UNIQUE(schedule_id, cycle_number) is what
-- prevents duplicate notifications for the same due cycle (FR-015, research.md §5).
CREATE TABLE notification (
    id INTEGER PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES maintenance_schedule(id),
    cycle_number INTEGER NOT NULL,
    projected_due_at TEXT NOT NULL,
    webhook_delivered BOOLEAN NOT NULL DEFAULT 0,
    webhook_delivery_error TEXT,
    acknowledged_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (schedule_id, cycle_number)
);
