-- Rider-controlled Strava sync and a display time zone (specs/023-settings-sync-and-timezone).
-- strava_sync_interval_minutes is NULL until the rider saves a value (the server's
-- STRAVA_SYNC_INTERVAL_MINUTES setting then applies). timezone only changes how UTC-recorded
-- times are shown; no stored time is converted.
ALTER TABLE account ADD COLUMN strava_sync_enabled BOOLEAN NOT NULL DEFAULT 1;
ALTER TABLE account ADD COLUMN strava_sync_interval_minutes INTEGER;
ALTER TABLE account ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';
