# Implementation Plan: 030 Install History Cleanup

**Branch**: `030-install-history-cleanup` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary

Three changes on the existing installation periods, with no schema change: (1) editing an open period can end it by entering a removed moment, which moves the part to storage at that moment; (2) rows of deleted parts get a "(deleted)" label and a Delete button; (3) deleting a part always shows a confirmation with a "Keep install history" checkbox, and unless kept, the part's periods are deleted. Plus the Delete button border.

## Technical Context

Python 3 / FastAPI / Jinja2 / HTMX as before. SQLite; **no migration** (`component_installation_period` rows are deleted or closed). Tests in `tests/db`, `tests/services`, `tests/routers`, `tests/test_ui_*`.

## Constitution Check (v1.3.0)

| Principle | Result | Notes |
|---|---|---|
| I Simplicity | Pass | Reuses `move_component` with an optional moment; no new tables |
| II Modular | Pass | Rules in services; routers map errors; templates render |
| III TDD | Pass (planned) | Tests first; old immediate-delete tests rewritten to the two-step flow |
| IV Security | Pass | All routes `require_account`; input validated; parameterised SQL |
| V Observability | Pass | Info log lines for ending an installation by edit and for deleting a part with or without history (ids only) |
| Stack/layout | Pass | No new dependency, file kind or directory |

## Source Code

```text
app/db/components.py                     # delete_periods_for_component
app/services/component_service.py        # move_component(moved_at), delete_component(keep_history), delete_consequences
app/services/component_history_service.py# update_period ends an open period via move to storage; describe_bike_history unchanged shape
app/services/builder_service.py          # delete_part(keep_history), delete_confirmation
app/routers/builder.py                   # /builder/delete: always confirm, keep_history
app/routers/components.py                # /components/{id}/delete: always confirm, keep_history
app/routers/component_history.py         # delete route allows deleted parts; edit forms carry removed fields
app/templates/partials/builder.html      # confirm block with the checkbox
app/templates/partials/confirm_delete.html # checkbox for the page-level flow
app/templates/components/install_history.html, bikes/install_history.html, components/install_period_form.html
tests/                                   # mirrors
```

## Design Decisions

1. Ending by edit: validate first (after install, not future in the zone, valid), then `move_component(storage, moved_at=removed)` which closes the part's and its sub-parts' periods at that moment; then recompute mileage for the part and its sub-tree. No maintenance entries (feature 022).
2. Deleting a part: `delete_component(..., keep_history=False)` deletes the part's own periods after soft-deleting it; sub-parts keep theirs.
3. The UI always confirms: the first POST (without `confirmed`) returns the confirmation; the service keeps its existing `ConfirmationRequiredError` behavior for callers that pass no flag.
4. A deleted part's rows are built from `get_including_deleted`; Delete is allowed for any closed period whether or not the part exists.
