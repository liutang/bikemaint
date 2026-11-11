-- ride_activity: a synced Strava activity, idempotent on strava_activity_id.
CREATE TABLE ride_activity (
    id INTEGER PRIMARY KEY,
    strava_activity_id INTEGER UNIQUE NOT NULL,
    strava_gear_id TEXT,
    bike_id INTEGER REFERENCES bike(id),
    distance_miles REAL NOT NULL,
    occurred_at TEXT NOT NULL,
    is_deleted_upstream BOOLEAN NOT NULL DEFAULT 0,
    synced_at TEXT NOT NULL
);

CREATE INDEX idx_ride_activity_bike_id ON ride_activity(bike_id);
CREATE INDEX idx_ride_activity_occurred_at ON ride_activity(occurred_at);

-- mileage_adjustment: audit trail of manual corrections (FR-009).
-- Invariant (enforced in app/services/, not the DB): exactly one of bike_id /
-- component_id is non-NULL.
CREATE TABLE mileage_adjustment (
    id INTEGER PRIMARY KEY,
    bike_id INTEGER REFERENCES bike(id),
    component_id INTEGER REFERENCES component(id),
    delta_miles REAL NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_mileage_adjustment_bike_id ON mileage_adjustment(bike_id);
CREATE INDEX idx_mileage_adjustment_component_id ON mileage_adjustment(component_id);
