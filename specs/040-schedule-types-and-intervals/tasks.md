# Tasks: 040 Schedule Service Types and Intervals

## Phase 1: Data
- [ ] T001 Tests first: `tests/db/test_migration_0015.py` (old rows and ids survive, new columns default, Rides/Hours row insertable, foreign keys intact), `tests/db/test_schedules.py` (new fields round trip; `complete` sets `baseline_at`), `tests/db/test_mileage_usage.py` (`usage_since`, `recent_usage_for_bike`). Watch fail.
- [ ] T002 Migration 0015, `rows.py`, `app/db/schedules.py`, `app/db/mileage.py`.

## Phase 2: Domain (US1, US2, US3, US4)
- [ ] T003 [US1] Tests first: `tests/models/test_schedule_request.py` (service types, kind/unit pairing, number > 0), `tests/services/test_schedule_service.py` (month and year arithmetic incl. month ends, weeks, rides and hours projection and overdue, part counts only installed rides, legacy schedules unchanged, one interval only).
- [ ] T004 [US1] `ScheduleRequest`; `schedule_service` (`create/update`, `_project`, `Projection.remaining*`, `next_due_text`).
- [ ] T005 [US2] Tests then code: `complete_schedule` recurring vs. one-time.
- [ ] T006 [US3] Tests then code: `notification_service` skips `notify` off; payload and summary units.

## Phase 3: Screens
- [ ] T007 [US1][US4] Tests first: `tests/routers/test_schedules.py` and `tests/test_ui_schedule_form.py` (fields, defaults, units per kind, 422 messages, legacy prefill, Service Type required on legacy edit). Update older tests posting `name`/`interval_*`.
- [ ] T008 [US1][US4] Router, `schedules/form.html`, `styles.css` (`:has`), `other_row.html`, dashboard text, contract docs.

## Phase 4: Wrap-up
- [ ] T009 `CLAUDE.md` note; full suite; PR; merge; confirm publish.
