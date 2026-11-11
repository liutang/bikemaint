-- Rides become a ride log the rider can edit (specs/006-feedback-round-2, M3).
-- ride_activity is rebuilt so rides without a Strava id (manual rides) are possible, and so
-- the rider's edits and deletions survive the next Strava sync.
CREATE TABLE ride_activity_new (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'strava',          -- 'strava' | 'manual'
    strava_activity_id INTEGER UNIQUE,              -- NULL for manual rides
    strava_gear_id TEXT,
    bike_id INTEGER REFERENCES bike(id),
    distance_miles REAL NOT NULL,
    occurred_at TEXT NOT NULL,
    note TEXT,
    is_deleted_upstream BOOLEAN NOT NULL DEFAULT 0,
    deleted_by_user BOOLEAN NOT NULL DEFAULT 0,
    user_modified BOOLEAN NOT NULL DEFAULT 0,       -- sync must not overwrite a rider's edit
    synced_at TEXT
);

INSERT INTO ride_activity_new (
    id, source, strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at,
    is_deleted_upstream, synced_at
)
SELECT id, 'strava', strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at,
       is_deleted_upstream, synced_at
FROM ride_activity;

DROP TABLE ride_activity;
ALTER TABLE ride_activity_new RENAME TO ride_activity;

CREATE INDEX idx_ride_activity_bike_id ON ride_activity(bike_id);
CREATE INDEX idx_ride_activity_occurred_at ON ride_activity(occurred_at);
