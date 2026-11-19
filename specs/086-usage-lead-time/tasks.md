---
description: "Task list for 086 usage lead time"
---

# Tasks: Usage Lead Time

**Input**: `specs/086-usage-lead-time/`. **Tests**: TDD. **Mock-up first**: T002 must be approved before T009 and T012.

## Phase 1: Setup

- [ ] T001 Confirm the branch (master merged in) and `.specify/feature.json`, and run the suite as the baseline.
- [ ] T002 Show the rider the final Lead time card and an urgent card whose ring reads "18 mi", and record approval here.

## Phase 2: Foundational

- [ ] T003 [P] Tests first in `tests/db/test_accounts.py`: after migration `0024_usage_leads.sql` the account has `lead_miles` 20, `lead_rides` 2 and `lead_hours` 2. `accounts.update_leads` saves them.
- [ ] T004 Add the migration, the row fields (`app/models/rows.py`) and `update_leads` (`app/db/accounts.py`).

## Phase 3: User Story 1 - Set how much left counts as due soon (P1)

- [ ] T005 [P] [US1] Tests first:
  - `tests/models/test_settings_requests.py`: the three fields are 0 or more, within their upper bounds, and whole numbers for rides.
  - `tests/services/test_settings_service.py`: `set_leads` saves all four.
- [ ] T006 [US1] Implement T005 in `NotificationSettingsRequest` and `settings_service.set_leads`.
- [ ] T007 [P] [US1] Route tests first in `tests/routers/test_settings.py`:
  - the card shows four fields and the summary "Currently D days, M miles, R rides or H hours, whichever comes first.";
  - an HTMX save answers the card with "Saved";
  - a bad value answers "Not saved" and changes nothing.
- [ ] T008 [P] [US1] Test first in `tests/services/test_backup_service.py`: the leads round-trip, and an older file keeps the defaults.
- [ ] T009 [US1] Implement T007 and T008: `settings/cards/lead.html`, the route in `app/routers/settings.py`, and `backup_service.SETTINGS`.

## Phase 4: User Story 2 - Due soon by what's left (P1)

- [ ] T010 [P] [US2] Tests first in `tests/services/test_schedule_service.py` for `is_due_soon`:
  - each unit at, just above and just under its lead;
  - by the date rule only;
  - a lead of 0;
  - a part in storage;
  - a period-only schedule;
  - an interval at or under its lead (due soon right after service);
  - overdue isn't due soon;
  - the `trigger` value.
- [ ] T011 [US2] Implement `Projection.on_bike`, `is_due_soon` and `due_status` using it in `app/services/schedule_service.py`.
- [ ] T012 [P] [US2] Tests first:
  - `tests/services/test_notification_service.py`:
    - a usage-triggered due soon records one notification with `projected_due_at` (the date, else today);
    - a second check records nothing;
    - muted and per-schedule notify off record nothing.
  - `tests/test_ui_attention.py`: the ring reads "18 mi" with its fill from `1 − 18/20`.
- [ ] T013 [US2] Implement T012: `notification_service.check_due_schedules` uses `is_due_soon` (the log line gains `trigger=`), and the ring values in `schedule_service` and `partials/ring.html`.
- [ ] T014 [US2] Test first, then confirm: SC-001, a replay of SLR7 Chain 3's 2026 cycle with a 20 mi lead, turns due soon at the ride that reaches 166 mi.

## Phase 5: Polish

- [ ] T015 [P] Amend 001 (due-soon rule), 040, 045, 061 and 003's ring contract, and update the CLAUDE.md "Notifications" and "Usage overdue" paragraphs.
- [ ] T016 Run the full suite, check the card and board by hand on a local server, and record the result.
- [ ] T017 Run `/speckit-analyze` and resolve any CRITICAL or HIGH finding.

## Dependencies

Phase 2 comes first. US1 and US2 are independent once it's done, except that US2's board test reads the leads from the account. T002 gates the templates.
