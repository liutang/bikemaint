# Tasks: 030 Install History Cleanup

Format: `- [ ] ID [Story] Description (files)`. Tests first (constitution III).

## US3-adjacent bug: button border (P1, small)

- [x] T001 [US2] Test first: the Delete button in `components/install_history.html` and `bikes/install_history.html` has class `btn` and not `btn-quiet`. Then change both templates.

## US1 — End an installation from the edit form (P1)

- [x] T002 [US1] Tests first: `tests/services/test_component_history_service.py` (updating an open period with a valid removed moment closes it, moves the part to storage, closes sub-parts' periods at that moment, recomputes mileage to count only rides before the moment, writes no maintenance entry; blank keeps it installed; removed not after install, in the future for the zone, or invalid is refused and changes nothing), `tests/services/test_component_service.py` (`move_component(..., moved_at=...)` closes periods at the given moment), `tests/routers/test_component_history.py` (edit form for an open period shows the optional removed fields; save with a valid moment redirects and moves the part to storage; bad moments 422 with a message beside the field; works with `?from_bike=` and returns to the bike's history; closed periods unchanged). Watch fail.
- [x] T003 [US1] `component_service.move_component(moved_at)`, `component_history_service.update_period` (end by edit), router `_parse` and edit template (removed fields for open periods, hint), log line.

## US2 — Label and remove deleted parts' entries (P1)

- [x] T004 [US2] Tests first: bike history rows of deleted parts read "<name> (deleted)" with no link and no Edit but a bordered Delete; `POST /install-periods/{id}/delete?from_bike=` works for a deleted part and removes only that row, mileage and other rows untouched; part-level history unchanged. Watch fail.
- [x] T005 [US2] `component_history_router._period_and_part` for delete includes deleted parts; template label and button.

## US3 — Delete a part, keep or remove its history (P1)

- [x] T006 [US3] Tests first: `tests/db/test_components_periods.py` (`delete_periods_for_component`), `tests/services/test_component_service.py` (`delete_component(keep_history=False)` removes the part's periods but not its sub-parts'; `keep_history=True` keeps them; `delete_consequences` wording for sub-parts, maintenance history and schedules), `tests/services/test_builder_service.py` (`delete_part(keep_history)`, `delete_confirmation`), `tests/routers/test_builder.py` and `tests/test_ui_pages.py` (every delete shows the confirmation first with an unchecked `keep_history` checkbox and Cancel; confirming without the box removes the part and its history from its own, its parent's and the bike's views; with the box keeps them labeled "(deleted)"; sub-parts keep history; sign-in required; a double submit deletes once). Rewrite the older one-click delete tests to the two-step flow. Watch fail.
- [x] T007 [US3] `components_db.delete_periods_for_component`, service and builder changes, routers, `builder.html` and `confirm_delete.html` checkbox, logs.

## Polish

- [x] T008 Docs, contracts and `CLAUDE.md` updated; suite 1132 passed. Analysis: every FR maps to tests (FR-001..FR-005 history service and router tests; FR-006/FR-007 bike history and delete-route tests; FR-008 border tests; FR-009..FR-011 builder/component delete tests; FR-012 sign-in via the existing route-redirect tests). Old one-click delete tests were rewritten to the confirm-first flow. Not checked in a browser; migration-free. Deleting a part now removes its history by default, a behavior change the rider asked for.
