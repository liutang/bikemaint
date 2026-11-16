---
description: "Task list for 074 time zone labels follow the season"
---

# Tasks: Time Zone Labels Follow the Season

**Input**: `specs/074-zone-label-season/` (spec.md, plan.md, research.md, quickstart.md)
**Tests**: required (constitution: TDD). Write each test first and watch it fail.

## Phase 1: Setup

- [x] T001 Confirm the branch `074-zone-label-season` and `.specify/feature.json` point at `specs/074-zone-label-season`

## Phase 2: User Story 1 - The time zone list reads the way clocks read today (P1)

**Goal**: entries show the offset and abbreviation in force when the page is shown, ordered by that offset.
**Independent test**: the service with `at` fixed in January and in July; Settings with the moment pinned.

- [x] T002 [US1] Tests first in `tests/services/test_clock_service.py`:
  - Replace the standard-offset tests with dated ones: January and July cases from spec US1 scenarios 1–4.
  - Ordering by the shown offset never goes down, in both months (SC-002).
  - London comes first among ties in January. UTC and Azores (no brackets, `+00`) tie in July.
  - An off-list saved zone reads `Current: (GMT+3) Europe/Istanbul` in both months.
  - Omitting `at` uses `clock_service._utc_now()`.
  - Run them and watch them fail.
- [x] T003 [US1] Tests first in `tests/routers/test_settings.py`:
  - Pin `clock_service._utc_now` to a January moment for the existing option and "Currently …" assertions.
  - Add a July case: New York reads `(GMT-4) America/New York (EDT)` and "Currently (GMT-4) America/New York (EDT)." (scenario 6, FR-004).
  - Watch it fail.
- [x] T004 [US1] In `app/services/clock_service.py`:
  - Add `_utc_now()` and `offset_minutes(name, at)`.
  - Make `_label(name, at)` use `at.astimezone(ZoneInfo(name))` for the offset and abbreviation.
  - Make `timezone_choices(current, at=None)` sort by `(offset_minutes(n, at), n != "Europe/London", n)`.
  - Remove `_standard_time` and `standard_offset_minutes`, and update the picker comment.
  - Run the two test files until they pass.

## Phase 3: Polish

- [x] T005 Amend `specs/023-settings-sync-and-timezone/spec.md` (US2 scenario 1, FR-006, Amendments line for 074) and `specs/023-settings-sync-and-timezone/contracts/routes.md` (Time zone section). Add a "Zone labels (feature 074)" note to `CLAUDE.md`.
- [x] T006 Run the full suite: `.venv/bin/python -m pytest -q`
- [x] T007 Check Settings in the browser against `quickstart.md` steps 1, 3 and 4

## Dependencies

T001 → T002, T003 (either order) → T004 → T005 → T006 → T007. One story, so the MVP is the whole list.
