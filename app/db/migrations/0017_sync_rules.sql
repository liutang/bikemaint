-- Sync rules (specs/060-sync-rules): which Strava rides count for a bike or part.
ALTER TABLE ride_activity ADD COLUMN sport_type TEXT;
ALTER TABLE ride_activity ADD COLUMN ride_type TEXT;
ALTER TABLE ride_activity ADD COLUMN activity_name TEXT;
ALTER TABLE ride_activity ADD COLUMN filtered_out INTEGER NOT NULL DEFAULT 0 CHECK (filtered_out IN (0, 1));

CREATE TABLE sync_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bike_id INTEGER REFERENCES bike(id) ON DELETE CASCADE,
    component_id INTEGER REFERENCES component(id) ON DELETE CASCADE,
    sports TEXT NOT NULL DEFAULT '',
    ride_types TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    CHECK ((bike_id IS NULL) <> (component_id IS NULL))
);
CREATE UNIQUE INDEX sync_rule_bike ON sync_rule(bike_id) WHERE bike_id IS NOT NULL;
CREATE UNIQUE INDEX sync_rule_component ON sync_rule(component_id) WHERE component_id IS NOT NULL;
