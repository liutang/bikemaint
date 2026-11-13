# Feature Specification: Screen Polish

**Feature Branch**: `031-screen-polish`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback: (1) cancelling a new schedule on a part should return to the part, not to the Maintenance due page; (2) in Install History, the places a part was installed in should be links when they still exist; (3) the "Edit starting mileage" link under Rides is redundant because each bike's and part's Edit screen already has the Baseline mileage field.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cancel Returns Where I Came From (Priority: P1)

As the rider adding a maintenance schedule to a part or bike, I want Cancel to take me back to that part or bike, so I don't lose my place.

**Why this priority**: Cancelling currently lands on a different screen (Maintenance due), which feels like being thrown out.

**Independent Test**: Open a wheel, choose Add schedule, then Cancel: the wheel's screen opens.

**Acceptance Scenarios**:

1. **Given** the New maintenance schedule form opened from a part, **When** the rider chooses Cancel, **Then** the part's own screen opens.
2. **Given** the form opened from a bike, **When** the rider chooses Cancel, **Then** the bike's own screen opens.
3. **Given** the form was shown again after a validation error, **When** the rider chooses Cancel, **Then** Cancel still returns to the part or bike.
4. **Given** an existing schedule being edited (reached from the Maintenance due page), **When** the rider chooses Cancel, **Then** the Maintenance due page opens, as before.
5. **Given** a schedule is saved, **When** the save completes, **Then** behavior is unchanged (the Maintenance due page opens).

---

### User Story 2 - Places in Install History Are Links (Priority: P2)

As the rider reading Install History, I want the place a part was installed in to be a link, so I can jump to that part or bike.

**Why this priority**: It removes a dead end when following where parts have been.

**Independent Test**: A tire was installed in a wheel on a bike. On the tire's Install History, the place reads as a link to the wheel; on the bike's Install History, the same.

**Acceptance Scenarios**:

1. **Given** a row whose place is a part that still exists, **When** it is shown (a part's "Installed on" column or a bike's "Placed in" column), **Then** the part's name is a link to that part's screen.
2. **Given** a row whose place is a bike that still exists, **When** it is shown, **Then** the bike's name is a link to that bike's screen.
3. **Given** a row whose place is a deleted part, a deleted bike, or Storage, **When** it is shown, **Then** it is plain text as before.
4. **Given** the links, **When** they are used by keyboard or assistive technology, **Then** they are ordinary links announced by their text.

---

### User Story 3 - No Redundant Starting Mileage Link (Priority: P3)

As the rider reading a Rides log, I want the starting-mileage row to be informational, so there is one place (the Edit screen's Baseline mileage) to change it.

**Why this priority**: The link duplicates the Baseline mileage field on the Edit screen.

**Independent Test**: Open a bike's Rides: the first row still shows the starting mileage but has no "Edit starting mileage" link.

**Acceptance Scenarios**:

1. **Given** a bike's or a part's Rides log, **When** it is shown, **Then** the first row still shows "Starting mileage", its miles, the source "Baseline" and the running total.
2. **Given** that row, **When** it is shown, **Then** it has no "Edit starting mileage" link.
3. **Given** the bike's or part's Edit screen, **When** it is shown, **Then** its Baseline mileage field is unchanged and is the way to change the starting mileage.

---

### Edge Cases

- A place that is a part inside another part links to the immediate parent part, as before it showed that name.
- A place whose part was deleted while its history was kept (feature 030) stays plain text.
- The starting-mileage row on a part's Rides log (read-only) is unchanged apart from not having a link.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cancel on the New maintenance schedule form MUST return to the screen of the bike or part it was opened for, including after a validation error; Cancel on an existing schedule's edit form MUST still return to the Maintenance due page.
- **FR-002**: In a part's Install History ("Installed on") and a bike's Install History ("Placed in"), a place that is an existing part MUST link to that part's screen and a place that is an existing bike MUST link to that bike's screen; other places (deleted parts or bikes, Storage) MUST be plain text.
- **FR-003**: The Rides log MUST NOT show an "Edit starting mileage" link; the starting-mileage row MUST remain with its values.

### Key Entities

- None new. The starting mileage shown on a Rides log is the bike's or part's baseline mileage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cancelling a new schedule returns to the part or bike in one click, 100% of the time.
- **SC-002**: Every place that is an existing part or bike in Install History is reachable in one click.
- **SC-003**: The Rides log has 0 links that duplicate the Edit screen's Baseline mileage field.

## Assumptions

- Saving a new schedule still goes to the Maintenance due page (not part of this request).
- The Rides "starting mileage" row and the Edit screen's "Baseline mileage" are the same stored value (confirmed against the code).
