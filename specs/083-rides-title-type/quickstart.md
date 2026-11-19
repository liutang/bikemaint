# Quickstart: 083 Ride Titles and Activity Types

1. **Migration:** start on a copy of the live database. Manual rides show their former note as the title, or "Manual Ride" when they had none, with type "Manual".
2. **A paired bike's Rides list:** columns are Date & time, Title, Miles, Moving time, Activity type, Total and Actions. Strava rides show their names and types, with any note under the title.
3. **Add a ride:** Title is pre-filled "Manual Ride". Change it to "Trainer" and save; it's listed as "Trainer", type "Manual".
4. **Edit a Strava ride:** the title and type are text, not fields, and Note is still there.
5. **Re-import:** a bike's older rides get their titles and types; an edited ride keeps its edits.
6. **Tests:** run `.venv/bin/python -m pytest -q`.
