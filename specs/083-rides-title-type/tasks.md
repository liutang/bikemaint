---
description: "Task list for 083 ride titles and activity types"
---

# Tasks: Ride Titles and Activity Types

**Input**: `specs/083-rides-title-type/`. **Tests**: TDD. **Mock-up first**: T002 must be approved before T012 and T014.

## Phase 1: Setup

- [ ] T001 Confirm the branch (master merged in) and `.specify/feature.json`, and run the suite as the baseline.
- [ ] T002 Show the rider the final Rides list and the Add, manual Edit and Strava Edit forms, and record approval here.

## Phase 2: Foundational

- [ ] T003 [P] Test first in `tests/models/test_sync_rules.py`: `sport_label("GravelRide") == "Gravel ride"`, `sport_label("TrailRun") == "Trail run"`, and `sport_label(None) == ""`.
- [ ] T004 Implement `sport_label` in `app/models/sync_rules.py`.
- [ ] T005 [P] Test first in new `tests/db/test_migration_0023.py`:
  - a manual ride with note "Trainer" gets `activity_name` "Trainer" and `note` NULL;
  - a manual ride with no note gets "Manual Ride";
  - Strava rides are unchanged.
- [ ] T006 Add `app/db/migrations/0023_manual_ride_titles.sql`.

## Phase 3: User Story 2 - Adding and editing a ride (P1)

- [ ] T007 [P] [US2] Tests first:
  - `tests/models/test_requests.py`: `RideRequest.title` is trimmed, at most 200 characters, and blank becomes None.
  - `tests/services/test_ride_service.py`:
    - `create_ride(title=…)` stores `activity_name`, and a blank title saves "Manual Ride";
    - `update_ride` of a manual ride changes its title;
    - `update_ride` of a Strava ride changes its note but never `activity_name` or `sport_type`.
- [ ] T008 [US2] Implement T007 in `app/models/requests.py`, `app/services/ride_service.py` and `app/db/mileage.py` (`create_manual_ride` and `update_ride` write `activity_name`).
- [ ] T009 [P] [US2] Test first in `tests/db/test_mileage.py`: upserting an edited Strava ride with a NULL name or type fills them, and keeps its miles, time and note. An unedited ride is updated as today. A ride on an archived bike is untouched.
- [ ] T010 [US2] Implement T009 in `upsert_ride_activity`.
- [ ] T011 [P] [US2] Route tests first in `tests/routers/test_rides.py`:
  - **Add form:** a Title field with value "Manual Ride", and no Note field.
  - **Manual Edit form:** a Title field.
  - **Strava Edit form:** the title and type as text, the hint "From Strava. Rename it there, then Re-import.", and a Note field.
  - **Posting:** a title on a Strava ride is ignored.
- [ ] T012 [US2] Implement T011 in `app/routers/rides.py` and `app/templates/rides/form.html`.

## Phase 4: User Story 1 - Rides are listed by title and type (P1)

- [ ] T013 [P] [US1] Tests first in `tests/routers/test_rides.py`:
  - **Headers:** exactly Date & time, Title, Miles, Moving time, Activity type, Total, and Actions on a bike's list.
  - **Strava rows:** the title, with a note in `small.ride-note`, and the type label.
  - **Manual rows:** the title and "Manual".
  - **An old Strava ride** has blank cells.
  - **Part and period lists** show the same columns, without Actions.
- [ ] T014 [US1] Implement T013 in `app/templates/rides/log.html` (Jinja filter `sport_label`, registered in `app/main.py`) and a `.ride-note` style.

## Phase 5: Polish

- [ ] T015 [P] Amend 006, 039, 053 and 060 (Amendments lines), and update `CLAUDE.md` ("Ride log" and "Ride moving time" paragraphs).
- [ ] T016 Run the full suite, run `quickstart.md` by hand on a copy of the live-shaped data, and record the result.
- [ ] T017 Run `/speckit-analyze` and resolve any CRITICAL or HIGH finding.

## Dependencies

Phase 2 comes first, then US2 (the forms and storage), then US1 (the list reads them). T002 gates the templates.
