---
description: "Task list for 084 quiet top bar"
---

# Tasks: Quiet Top Bar

**Input**: `specs/084-quiet-top-bar/`. **Tests**: TDD. The rider approved the mock-ups on 2026-11-18.

## Phase 1: Setup

- [ ] T001 Confirm the branch (master merged in) and `.specify/feature.json`, and run the suite as the baseline.

## Phase 2: User Story 1 - A shorter Maintenance link (P1)

- [ ] T002 [P] [US1] Tests first:
  - every signed-in page's top bar links `/maintenance/due` with the text "Maintenance", not "Maintenance due";
  - the Settings Mute card reads "Schedules still appear under Maintenance."
- [ ] T003 [US1] Implement T002 in `app/templates/layout.html` and `app/templates/settings/cards/mute.html`.

## Phase 3: User Story 2 - The sync dot on its own (P1)

- [ ] T004 [P] [US2] Tests first in `tests/services/test_sync_status_service.py`, with `now` pinned:
  - `sync_hover` for each state, and for just now, minutes, hours, days and never.
  - `settings_line` for the four sentences, including the local time in the saved zone.
- [ ] T005 [US2] Implement `sync_hover` and `settings_line` in `app/services/sync_status_service.py`, and register them as Jinja globals.
- [ ] T006 [P] [US2] Route tests first:
  - the top bar's `.sync-status` has no text, and has `title` and `aria-label` equal to the hover text;
  - the Strava card has `p.sync-line` with the matching state class and sentence.
- [ ] T007 [US2] Implement T006 in `layout.html` and `settings/cards/strava.html`, and update `styles.css` (no text spacing; the phone rule that gave `.sync-status` its own row is removed).

## Phase 4: User Story 3 - An icon-only Sign out (P2)

- [ ] T008 [P] [US3] Test first: the Sign out button is `btn btn-icon`, with `aria-label` and `title` "Sign out" and no visible text, and posting still signs out.
- [ ] T009 [US3] Implement T008 in `layout.html`.

## Phase 5: Polish

- [ ] T010 [P] Amend 003 (FR-006a and FR-006b presentation, and its UI contract), 002's header contract, 045 and 070, and update the `CLAUDE.md` "Sync dot" and "Last-sync indicator" paragraphs and the nav label wording.
- [ ] T011 Run the full suite, check the top bar by hand in the browser at desktop and phone widths, and record the result.
- [ ] T012 Run `/speckit-analyze` and resolve any CRITICAL or HIGH finding.
