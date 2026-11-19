# Research: 083 Ride Titles and Activity Types

## 1. Where a manual ride's title lives

- **Decision**: `ride_activity.activity_name`, the same column as Strava titles. Migration 0023 moves existing manual notes there ("Manual Ride" when blank) and clears their `note`.
- **Rationale**:
  - One column means one rule for the list: Title = `activity_name`.
  - Sync rules can't be affected, because manual rides are `user_modified = 1` and always match (`part_ride_ok`, `apply_bike_rule` only touches unedited Strava rides).
- **Alternative considered**: keeping manual titles in `note`. Rejected: the list would need a rule per source, and Strava rides still need `note` for the rider's own notes.

## 2. Activity type labels

- **Decision**: `sync_rules.sport_label(code)` returns:
  - `SPORTS[code]` when the code is known;
  - otherwise the code split at capitals, in sentence case (`TrailRun` reads "Trail run");
  - `""` for `None`.

  Manual rides show "Manual" (the template decides by `source`).

## 3. Read-only Strava title and type

- **Decision**: the Edit form of a Strava ride shows them as text, with the hint "From Strava. Rename it there, then Re-import." `RideRequest.title` is ignored for Strava rides: the service never writes `activity_name` or `sport_type` from the form for them.
- **Rationale**: spec FR-002. Saving the form still marks the ride edited (unchanged behavior).

## 4. Filling missing details on edited rides

- **Decision**: after the normal upsert, which skips edited rides, an extra parameterized UPDATE sets `activity_name = COALESCE(activity_name, ?)` and `sport_type = COALESCE(sport_type, ?)` where `strava_activity_id = ? AND user_modified = 1`, and the bike isn't archived (079).
- **Rationale**: spec FR-005. Nothing else about an edited ride changes.

## 5. Blank manual title

- **Decision**: a blank title saves as "Manual Ride". The form pre-fills it, so blank only happens when the rider clears it.
