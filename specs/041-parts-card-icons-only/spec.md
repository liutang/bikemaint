# Feature Specification: Parts Card Icons Only

**Feature Branch**: `041-parts-card-icons-only`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: "The Parts on this bike card should only have the part name and type on the left and garage and trash can icons on the right. I don't need the arrows. They're redundant." Supersedes the reorder arrows (004) and the Move to… control (020, 035 FR-003) on that card.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Quiet Row With Two Actions (Priority: P1)

Each part row on the Parts card shows its drag handle, icon, name (a link) and type on the left, and only the Garage and Trash icon buttons on the right.

**Independent Test**: Open a bike with a nested part; no row has an arrow button or a Move to control.

**Acceptance Scenarios**:

1. **Given** a bike with parts, **When** the Parts card is shown, **Then** each row's actions are exactly Garage ("Garage <name> (move to storage)") and Trash ("Trash <name>").
2. **Given** siblings, **When** shown, **Then** there are no Move up, Move down or Move to controls.
3. **Given** a part, **When** the rider wants to reorder it or put it somewhere else, **Then** they drag it (reordering within the same parent, or dropping on another part, the bike or storage); the server routes behind drag and drop are unchanged.
4. **Given** the Add a part panel, **When** shown, **Then** its "Add to…" controls are unchanged.

### Edge Cases

- Garage and Trash behave exactly as before (Trash still asks first).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Part rows on the Parts card MUST show only Garage and Trash as action buttons.
- **FR-002**: The reorder arrows and the Move to… control MUST NOT be shown on that card; drag and drop and the `/builder/move` route are unchanged.

### Key Entities

- None.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No part row on the Parts card has more than 2 action buttons.

## Assumptions

- The drag handle and part icon stay on the left as drag affordances.
