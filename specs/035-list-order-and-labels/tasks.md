# Tasks: 035 List Order and Labels

## Phase 1: User Story 1 - Rides order (P1)

- [ ] T001 [US1] Test first in `tests/services/test_ride_service.py`: rows are rides newest first then the start row last; no-ride bike has only the start row; running totals unchanged. Update existing assertions that expect the start row first (lines ~43, 132, 214, 225). Watch fail.
- [ ] T002 [US1] `app/services/ride_service.py`: return `[*built, start]` instead of `[start, *built]`; update the `RideLog.rows` comment.

## Phase 2: User Story 2 - Install History order (P1)

- [ ] T003 [US2] Test first in `tests/services/test_component_history_service.py`: a part's `describe_history` lists latest installed first, ties by newest id; bike history stays latest first. Watch fail.
- [ ] T004 [US2] `app/services/component_history_service.py` `describe_history`: iterate periods sorted by `(installed_at, id)` descending.

## Phase 3: User Story 3 - Move control icon (P2)

- [ ] T005 [US3] Test first in `tests/routers/test_builder.py`: no visible text "Move to…" on the Parts card; the control has `aria-label="Move <part> to…"` and the arrow-right icon; the move form is still present. Watch fail.
- [ ] T006 [US3] `app/templates/partials/builder.html`: replace the summary text with `ui_icons.arrow_right()`, add `aria-label` and `title`.

## Phase 4: Wrap-up

- [ ] T007 Full suite green; amend `CLAUDE.md` only if it mentions the old order (otherwise none); PR; merge; confirm publish.
