# Quickstart: Modern UI

Validates the feature against the spec's user stories. Assumes feature 001 is built and the
environment variables from the project README are set.

## Prerequisites

1. Install and run as usual: `.venv/bin/pip install -e ".[dev]"`, then `uvicorn app.main:app --reload`.
2. Seed some data (via the UI or a scratch database): two bikes, a three-level component tree
   (wheel → rim → tire), one component in storage, and schedules in each state — overdue,
   inside the lead-time window, far out, and mileage-only with no ride history.

## Automated checks

```bash
.venv/bin/python -m pytest -q
```

Expected: the existing suite plus `tests/test_ui_*.py`, `tests/models/test_form_errors.py` and
`tests/services/test_schedule_status.py` all pass (SC-004 contrast and the asset-size budget are
asserted there).

## Scenario 1 — App shell (User Story 1)

1. Open `/login` signed out: styled page, brand only, no nav links.
2. Sign in; visit Garage, Maintenance due, Settings: same header on each, the current section is
   highlighted, **Sign out** works.
3. Switch the OS between light and dark (or emulate it): the theme follows with no reload and no flash.
4. Resize to 360 px: no horizontal page scrolling; nav stays reachable; tap targets ≥ 44 px.

## Scenario 2 — Garage and tree (User Story 2)

1. Garage shows bikes as cards with name, type, mileage; storage in its own section.
2. Open a bike: the tree shows nesting depth; collapse and expand a branch; each item shows type and mileage.
3. Use a fresh database: empty states for no bikes and empty storage.
4. Delete a bike that has components: a destructive confirmation appears (inline), naming what will be deleted, with a cancel path.

## Scenario 3 — Dashboard (User Story 3)

1. Each row shows the right badge (text + icon + color); overdue is identifiable in under 5 seconds without color.
2. Click **Mark done**: only that row updates, no page reload.
3. With an unacknowledged alert, dismiss it: it disappears in place.
4. With no schedules: empty state with guidance. At 360 px: rows stack, no horizontal page scroll.

## Scenario 4 — Forms (User Story 4)

1. Submit each form with invalid input: entries are kept, the error sits next to the field, plus a summary.
2. Tab through a form: a visible focus ring on every control, in order.
3. Primary / secondary / destructive buttons are visually distinct.

## Cross-cutting

- Disable JavaScript: every flow still works with normal navigation and form posts.
- Enable "reduce motion" in the OS: no transitions.
- Browser network panel: per page, only the HTML, `styles.css` and `htmx.min.js` load (no third-party origins), total CSS+JS under 150 KB.
