# Feature Specification: Maintenance Due Row Actions

**Feature Branch**: `072-due-row-actions`
**Created**: 2026-11-16
**Input**: User testing after 071: on Maintenance due, "Everything else" rows still show a text "Mark done" button; it should be a checkbox icon like the other row actions. The gaps between the three row buttons are uneven (Delete sits further away).

## User Scenarios & Testing
1. **Given** an "Everything else" row, **Then** its actions are three icon buttons in this order: Mark done (check), Edit (pencil), Delete (trash), each with a tooltip and accessible name.
2. **Given** those buttons, **Then** the space between each pair is the same.
3. **Given** Mark done, **Then** it still completes the task in place (same HTMX behavior) and ignores a double click.

## Requirements
- **FR-001**: `partials/other_row.html` puts the three buttons in one `.other-actions` group with equal gaps; Mark done is `btn btn-icon` with `aria-label="Mark done"`, `title="Mark done"` and the check icon.

## Success Criteria
- **SC-001**: The three buttons are evenly spaced at every width.

## Assumptions
- The urgent cards keep their wide "Mark done" button (the main action of a card).
