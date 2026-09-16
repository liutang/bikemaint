-- account: the signed-in rider and their Strava connection.
CREATE TABLE account (
    id INTEGER PRIMARY KEY,
    strava_athlete_id INTEGER UNIQUE NOT NULL,
    strava_access_token TEXT NOT NULL,
    strava_refresh_token TEXT NOT NULL,
    strava_token_expires_at TEXT NOT NULL,
    strava_connected_at TEXT NOT NULL,
    strava_connection_stale BOOLEAN NOT NULL DEFAULT 0,
    notification_webhook_url TEXT,
    notification_lead_time_days INTEGER NOT NULL DEFAULT 7,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- bike: a top-level, ridable item.
CREATE TABLE bike (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    bike_type TEXT,
    strava_gear_id TEXT UNIQUE,
    strava_paired_at TEXT,
    manual_baseline_mileage REAL NOT NULL DEFAULT 0,
    total_mileage REAL NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- component: self-referential tree; parent is a bike, another component, or nothing (storage).
-- Invariant (enforced in app/services/, not the DB): at most one of parent_bike_id /
-- parent_component_id is non-NULL at a time.
CREATE TABLE component (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    component_type TEXT NOT NULL,
    parent_bike_id INTEGER REFERENCES bike(id),
    parent_component_id INTEGER REFERENCES component(id),
    manual_baseline_mileage REAL NOT NULL DEFAULT 0,
    total_mileage REAL NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_component_parent_bike_id ON component(parent_bike_id);
CREATE INDEX idx_component_parent_component_id ON component(parent_component_id);

-- component_installation_period: when a component was attached to a given parent,
-- so historical ride mileage can be attributed correctly even after a component moves.
CREATE TABLE component_installation_period (
    id INTEGER PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES component(id),
    parent_bike_id INTEGER REFERENCES bike(id),
    parent_component_id INTEGER REFERENCES component(id),
    installed_at TEXT NOT NULL,
    removed_at TEXT
);

CREATE INDEX idx_installation_period_component_id ON component_installation_period(component_id);
CREATE INDEX idx_installation_period_open ON component_installation_period(component_id, removed_at);
