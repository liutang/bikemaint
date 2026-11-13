# Tasks: 022 Install History Split From Maintenance History

**Input**: `specs/022-install-history-split/` (spec.md, plan.md, research.md, data-model.md, contracts/routes.md, quickstart.md)

**Tests**: Required and written first (constitution III): failing test, then the minimal code.

Format: `- [ ] ID [P] [Story] Description (file paths)`.

## Phase 1: User Story 1 — Maintenance history is only maintenance (P1)

**Independent test**: add, move and delete parts; no entries appear in any maintenance history; logged services remain.

- [x] T001 [US1] Tests first. Rewrite `tests/services/test_part_events.py` to assert that adding, moving, removing, deleting a part and deleting a bike write nothing to any maintenance history (keep the reorder, confirmation and "real maintenance still confirms" tests); update `tests/services/test_maintenance_service.py` (move keeps the logged service and writes no event) and `tests/services/test_component_history_service.py` (logging and deleting a period by hand writes no entry); update `tests/routers/test_maintenance.py` (history pages show no add/remove rows, no `entry-event` class, no "Parts" tag). Add `tests/db/test_remove_part_events.py`: with migrations applied up to 0009, insert one `service` and two `event` rows, apply `0010_remove_part_event_entries.sql`, assert only the service row remains and that a service whose text starts with "Added" survives. Watch them fail.
- [x] T002 [US1] `app/db/migrations/0010_remove_part_event_entries.sql`: `DELETE FROM maintenance_log_entry WHERE kind = 'event';`.
- [x] T003 [US1] `app/services/component_service.py`: delete `_log_event`, `_log_added`, `_log_removed`, `_parent_name`, `_entity` if unused, and every call (create, move, delete, `detach_to_storage` including its `deleted_parent_name` event). `app/services/component_history_service.py`: delete `_log_event` and its two calls in `log_period` and `delete_period`.
- [x] T004 [P] [US1] `app/templates/maintenance/history_list.html`: drop the `entry-event` row class, the "Parts" tag and the `entry.kind == "event"` time branch; `app/static/styles.css`: remove `.entry-event` and `.entry-tag`. Update `docs`: note in `specs/006-feedback-round-2/spec.md` that FR-008 and US2 scenarios 1–3 are superseded by 022.

## Phase 2: User Story 2 — A part's installs live in its Install History (P1)

- [x] T005 [US2] Regression test in `tests/services/test_component_history_service.py`: after add, move to another bike and move to storage, the part's `describe_history` shows each period in order (already true; the test pins it now that events are gone). No code change expected.

## Phase 3: User Story 3 — A bike's Install History (P2)

**Independent test**: put a chain on a bike, move it to storage, add another; the bike's page lists both, newest first.

- [x] T006 [US3] Tests first: `tests/db/test_components_periods.py` (`list_periods_for_bike(conn, bike_id)` returns periods whose `parent_bike_id` is the bike, newest `installed_at` first, including nested parts and soft-deleted parts, excluding other bikes), `tests/services/test_component_history_service.py` (`describe_bike_history(bike_id)` rows have part name, kind display name, placed-in label (parent part, the bike, or "a deleted part"), installed, removed or None, a link flag false for deleted parts; a part moved between bikes appears on each bike once), `tests/routers/test_component_history.py` (`GET /bikes/{id}/install-history`: 200 with rows newest first and "Still installed"; empty state; 404 for an unknown bike; sign-in required; no form controls; part names link to `/components/{id}`), `tests/routers/test_builder.py` or `tests/test_ui_pages.py` (the bike's action row has an "Install history" button beside "Maintenance history"; a part's row does not gain a second one). Watch them fail.
- [x] T007 [US3] `app/db/components.py`: `list_periods_for_bike`; `app/services/component_history_service.py`: `describe_bike_history`; `app/routers/component_history.py`: `GET /bikes/{bike_id}/install-history` (name `bike_install_history`); `app/templates/bikes/install_history.html` (read-only table, empty state, breadcrumb); `app/templates/partials/part_actions.html`: "Install history" button for bikes.

## Phase 4: Polish

- [x] T008 Update `specs/015-component-install-history/spec.md` (FR-009 superseded: no maintenance events), `specs/015-component-install-history/contracts/routes.md` and the 001/015 contract cross-links for the new route; update `CLAUDE.md` (maintenance history is service-only; bike and part Install History; migration 0010).
- [x] T009 Full suite: 950 passed. Analysis: every FR (001–009) maps to a test (FR-001/003 `test_part_events.py`, FR-002 `test_remove_part_events.py`, FR-004/FR-005/FR-006/FR-007/FR-008/FR-009 the db, service and router tests); route coverage re-walked, no uncontracted route. No CRITICAL/HIGH findings. LOW: the new screen's look and the manual quickstart were not checked in a browser by Claude; migration 0010 deletes data on first start, which is intended but not reversible (the rider may want a backup of the data volume before pulling).

## Phase 5: Amendment from user testing (branch 024-bike-install-history-editable)

- [x] T010 [US4] Tests first: `tests/routers/test_component_history.py` (bike page shows "Log a period" and per-row Edit/Delete rules; `GET /bikes/{id}/install-history/new` and `POST /bikes/{id}/install-history` log a period for a chosen part on that bike, redirect back to the bike history, recompute mileage, and re-show the form with a message for each invalid case; edit and delete with `?from_bike=ID` return to the bike's history, without it to the part's; deleted parts have no Edit/Delete; sign-in required; the part's own history shows the same period), `tests/services/test_component_service.py` (`list_all_parts` returns active parts only, by name). Watch them fail.
- [x] T011 [US4] `app/db/components.py` `list_active`; `app/services/component_service.py` `list_all_parts`; `app/routers/component_history.py` (new bike form and create routes; optional `from_bike` on the edit, update and delete routes with validated integer and safe redirect); `app/templates/bikes/install_history.html` ("Log a period", Edit, Delete); `app/templates/bikes/install_period_form.html` (part chooser, optional inside-part chooser, dates); `app/templates/components/install_period_form.html` (carry `from_bike` in the action and Cancel link).
- [x] T012 Contracts and `CLAUDE.md` updated; full suite 1052 passed; every US4 scenario maps to a test (log, validation, overlap, edit and delete returning to the bike, live period refused, deleted parts without controls, sign-in, bad `from_bike`); a regression test pins that logged maintenance entries keep Edit and Delete. Not checked in a browser.

## Dependencies

- T001 → T002 → T003 → T004 (red, then the migration and the removals).
- T005 can run any time after T003.
- T006 → T007 (red, green). US3 needs only the existing periods, so it can start once T001–T004 are green.
- T008–T009 last.

## Implementation Strategy

MVP is Phase 1 (the history is clean). Then the bike screen. The suite stays green at the end of each phase.
