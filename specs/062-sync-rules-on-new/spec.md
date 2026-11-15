# Feature Specification: Sync Rules When Adding a Bike or Part

**Feature Branch**: `062-sync-rules-on-new`
**Created**: 2026-11-15
**Input**: User testing feedback: the sync rules should appear when adding a new bike or part, so the rider does not have to add it and then go back to Edit (extends specs/060-sync-rules).

## User Scenarios & Testing

### User Story 1 - Set Rules While Adding (Priority: P1)
**Acceptance Scenarios**:
1. **Given** the Add Bike or Add part form, **Then** a Sync rules section with Sport, Ride type and Keywords (same fields and wording as Edit) is part of the form; it is saved by the form's own Save button (no separate Save rules button).
2. **Given** rules filled in and the form saved, **Then** the new bike or part is created with that rule (and it is applied like a saved Edit rule).
3. **Given** nothing filled in, **Then** no rule is stored (same as no rule).
4. **Given** invalid rules (unknown choice, too long keywords) or other invalid fields, **Then** the form is refused with 422, nothing is created, and what was typed (including the rule choices) is kept, with the rule message beside the Sync rules.
5. **Given** the Edit screens, **Then** they are unchanged (own Save rules form).

### Edge Cases
- Parts added by dragging from the palette have no form and start with no rule; rules are set on Edit.

## Requirements
- **FR-001**: `GET /bikes/new` and `GET /components/new` MUST show the Sync rules fields inside the create form.
- **FR-002**: `POST /bikes` and `POST /components` MUST validate the rule before creating, create the item, then save a non-empty rule for it.
- **FR-003**: The field markup is shared with the Edit panel (one macro).

## Success Criteria
- **SC-001**: A rider can add a bike with a rule in one save and its Edit screen shows that rule.
