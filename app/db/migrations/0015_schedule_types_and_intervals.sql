-- Schedule service types and one interval of any unit (specs/040-schedule-types-and-intervals).
-- The old table-level CHECK required a mileage or a day interval, which schedules by rides,
-- hours, months or years do not have, so the table is rebuilt (SQLite cannot drop a CHECK).
-- Foreign keys are switched off for the rebuild only: notification.schedule_id keeps pointing at
-- the same ids.
PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE maintenance_schedule_new (
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
    service_type TEXT,
    interval_kind TEXT CHECK (interval_kind IS NULL OR interval_kind IN ('usage', 'period')),
    interval_value REAL CHECK (interval_value IS NULL OR interval_value > 0),
    interval_unit TEXT CHECK (interval_unit IS NULL
        OR interval_unit IN ('miles', 'rides', 'hours', 'years', 'months', 'weeks')),
    is_recurring INTEGER NOT NULL DEFAULT 1,
    notify INTEGER NOT NULL DEFAULT 1,
    baseline_at TEXT,
    CHECK (interval_miles IS NOT NULL OR interval_days IS NOT NULL OR interval_kind IS NOT NULL)
);

INSERT INTO maintenance_schedule_new (
    id, bike_id, component_id, name, interval_miles, interval_days, baseline_mileage,
    baseline_date, cycle_number, is_active, created_at, updated_at
)
SELECT id, bike_id, component_id, name, interval_miles, interval_days, baseline_mileage,
       baseline_date, cycle_number, is_active, created_at, updated_at
FROM maintenance_schedule;

DROP TABLE maintenance_schedule;
ALTER TABLE maintenance_schedule_new RENAME TO maintenance_schedule;
CREATE INDEX idx_maintenance_schedule_bike_id ON maintenance_schedule(bike_id);
CREATE INDEX idx_maintenance_schedule_component_id ON maintenance_schedule(component_id);

COMMIT;
PRAGMA foreign_keys = ON;
