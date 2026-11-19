# Implementation Plan: Ride Titles and Activity Types

**Branch**: `083-rides-title-type` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

**Storage:**
- Every ride's title lives in `ride_activity.activity_name`.
  - Strava rides already store it (060).
  - Manual rides get theirs from migration `0023_manual_ride_titles.sql`, which moves each manual ride's note into `activity_name` ("Manual Ride" when blank) and clears its note.
- `note` stays for Strava rides only.

**Screens:**
- **Rides lists** (`rides/log.html`) show Title (with a Strava note in small text under it) and Activity type (a readable label from `sync_rules.sport_label`, or "Manual") instead of Source and Note.
- **The ride form:**
  - Add, and Edit of a manual ride: a Title field, pre-filled "Manual Ride", replaces Note.
  - Edit of a Strava ride: the title and type show as text, and Note stays.

**Re-import:** it fills a missing title or type on an edited Strava ride, and changes nothing else about it.

Decisions are in [research.md](research.md), and markup in [contracts/ui-contract.md](contracts/ui-contract.md).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: none new
**Storage**: SQLite, migration `0023_manual_ride_titles.sql` (data only, plain SQL)
**Testing**: pytest. Model, service, db and route tests for each scenario; the migration is tested on seeded manual rides.
**Target Platform**: self-hosted Linux container
**Constraints**:
- sync rules are unchanged, because manual rides stay `user_modified = 1` and always match (060);
- no script.

**Scale/Scope**: about 7 app modules, 2 templates, and amendments to 006, 039, 053 and 060.

## Constitution Check

- **Fixed stack**: no change. PASS
- **Layout**:
  - The sport labels live in `app/models/sync_rules.py`, which already has the list.
  - The form field change is in `app/models/requests.py` (`RideRequest.title`).
  - Ride CRUD stays in `ride_service`, and the queries in `app/db/mileage.py`.

  PASS
- **I. Simplicity**: one title column for every ride, rather than a second manual-title column. PASS
- **III. TDD**: every scenario gets a failing test first. PASS
- **IV. Security**: the title is validated (max 200 characters, trimmed), and SQL stays parameterized. PASS
- **V. Observability**: ride add and edit log lines are unchanged. The title isn't logged (it's free text). PASS
- **Git**: one branch, one PR. PASS

## Project Structure

```text
app/db/migrations/0023_manual_ride_titles.sql   UPDATE manual rides: activity_name <- note or 'Manual Ride'; note <- NULL
app/models/sync_rules.py                        sport_label(code): SPORTS label, else CamelCase -> "Trail run"
app/models/requests.py                          RideRequest.title (manual), note kept (Strava)
app/services/ride_service.py                    create/update manual: title; Strava edit: note only
app/db/mileage.py                               create_manual_ride/update_ride write activity_name;
                                                upsert_ride_activity fills missing name/type on edited rides
app/routers/rides.py                            form context by source
app/templates/rides/log.html, rides/form.html
tests/models/test_sync_rules.py, tests/models/test_requests.py, tests/services/test_ride_service.py,
tests/db/test_mileage.py, tests/db/test_migration_0023.py, tests/routers/test_rides.py
```

## Before building the screens

The final Rides list and form mock-up goes to the rider before the template tasks.

## Complexity Tracking

None.
