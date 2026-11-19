# Feature Specification: Maintenance Due Row Actions

**Feature Branch**: `072-due-row-actions`
**Created**: 2026-11-16
**Input**: User testing after 071: on Maintenance due, "Everything else" rows still show a text "Mark done" button; it should be a checkbox icon like the other row actions. The gaps between the three row buttons are uneven (Delete sits further away).

## User Scenarios & Testing
1. **Given** an "Everything else" row, **Then** its actions are three icon buttons in this order: Mark done (check), Edit (pencil), Delete (trash), each with a tooltip and accessible name.
2. **Given** those buttons, **Then** the space between each pair is the same.
3. **Given** Mark done, **Then** it still completes the task in place (same HTMX behavior) and ignores a double click.
4. *(Added by branch `082-mark-done-width`, 2026-11-18.)* **Given** an urgent card, overdue or due soon, **Then**:
   - its Mark done button is as wide as its text, like every other button;
   - Edit and Delete are icon buttons pushed to the card's right edge, with Mark done at the left;
   - the overdue card's Mark done stays orange (primary).

## Requirements
- **FR-002** *(branch `082-mark-done-width`)*: On urgent cards (`partials/attention_card.html`, `.attention-actions`), Mark done MUST keep its natural width; it must not stretch. Edit and Delete MUST sit at the right edge of the card.
- **FR-001**: `partials/other_row.html` puts the three buttons in one `.other-actions` group with equal gaps; Mark done is `btn btn-icon` with `aria-label="Mark done"`, `title="Mark done"` and the check icon.

## Success Criteria
- **SC-001**: The three buttons are evenly spaced at every width.

## Assumptions
- ~~The urgent cards keep their wide "Mark done" button (the main action of a card).~~ Replaced by FR-002. The rider, 2026-11-18: "the Mark done button for the overdue maintenance tasks is too wide. it should match the width of the text like all the other buttons in the app." They chose both overdue and due-soon cards, with Edit and Delete right-justified, after a before/after mock-up.

## Amendments

- **2026-11-18 (branch `082-mark-done-width`)**: FR-002 and scenario 4. Urgent cards' Mark done is natural width, with Edit and Delete at the right edge.
