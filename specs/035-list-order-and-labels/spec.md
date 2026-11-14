# Feature Specification: List Order and Labels

**Feature Branch**: `035-list-order-and-labels`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: (1) the starting mileage should be last in the Rides list; (2) Install History should list the latest installation on top; (3) the "Move to…" text on the Parts card is unnecessary because the icons are self-explanatory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rides Read Newest to Oldest, Ending at the Starting Mileage (Priority: P1)

The Rides list shows rides newest first. The "Starting mileage" row is the oldest fact, so it belongs at the bottom, where the list ends.

**Why this priority**: The list is in descending order, so a starting row at the top reads as if it were the newest entry.

**Independent Test**: Open a bike's Rides with a few rides and confirm the starting row is last.

**Acceptance Scenarios**:

1. **Given** a bike with rides, **When** Rides opens, **Then** rides are newest first and "Starting mileage" is the last row.
2. **Given** a bike with no rides, **When** Rides opens, **Then** "Starting mileage" is the only row.
3. **Given** any rides list, **When** it is shown, **Then** each row's running total is unchanged (the starting row carries the baseline, each later row adds up from it).

---

### User Story 2 - Install History Shows the Latest First (Priority: P1)

A part's Install History and a bike's Install History both list rows by installed date and time, latest on top.

**Why this priority**: The current installation is what the rider wants to see first; a part's list currently starts with the oldest.

**Independent Test**: Give a part three periods and confirm the order on its Install History, then check a bike's.

**Acceptance Scenarios**:

1. **Given** a part with several installation periods, **When** its Install History opens, **Then** the period installed most recently is first and the oldest last.
2. **Given** a bike's Install History, **When** it opens, **Then** rows are in the same latest-first order (unchanged).
3. **Given** two periods installed at the same moment, **When** listed, **Then** the one created later is first.

---

### User Story 3 - Parts Card Move Control Is an Icon (Priority: P2)

In the Parts on this bike card, each part's "Move to…" button shows only an icon. Screen readers still announce it as "Move <part> to…".

**Why this priority**: Cosmetic cleanup; the icons beside it already make the row self-explanatory.

**Independent Test**: Open a bike with parts and confirm no row shows the words "Move to…" while the control still works.

**Acceptance Scenarios**:

1. **Given** a part with places to move to, **When** the card is shown, **Then** the control displays the arrow-right icon and no "Move to…" text.
2. **Given** the control, **When** inspected by assistive technology, **Then** its name is "Move <part name> to…".
3. **Given** the control is opened, **When** a place is chosen and submitted, **Then** the part moves exactly as before.

### Edge Cases

- A part with no places to move to still shows no move control.
- The "Add to…" control in the Add a part panel is unchanged.
- Up and down arrows are unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Rides list MUST show rides newest first with the "Starting mileage" row last; running totals MUST be unchanged.
- **FR-002**: A part's Install History MUST list periods latest installed first, ties broken by newest entry first; a bike's MUST stay latest first.
- **FR-003**: The tree's move control MUST show the arrow-right icon with no visible text and MUST have the accessible name "Move <part name> to…"; its behavior MUST be unchanged.

### Key Entities

- None new.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every Rides list, the starting row is the last row (100% of cases).
- **SC-002**: On every Install History, no row is listed above a row installed later.
- **SC-003**: The words "Move to…" appear on no row of the Parts card.

## Assumptions

- Only the display order changes; stored data and totals do not.
- Rides and install history layouts are otherwise unchanged.
