-- specs/083: a manual ride's title lives in activity_name, like a Strava ride's. Its note becomes its
-- title ("Manual Ride" when it had none), and the note is cleared: manual rides have no separate note.
UPDATE ride_activity
SET activity_name = COALESCE(NULLIF(TRIM(note), ''), 'Manual Ride'),
    note = NULL
WHERE source = 'manual';
