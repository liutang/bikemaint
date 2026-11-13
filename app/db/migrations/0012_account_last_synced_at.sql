-- When the most recent Strava sync run finished successfully (specs/003-cockpit-theme, FR-006a).
-- The top-bar "last synced" label used to be derived from ride rows, which only change when a
-- ride does, so it stood still while syncs found nothing new. NULL until a run is recorded.
ALTER TABLE account ADD COLUMN strava_last_synced_at TEXT;
