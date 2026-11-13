# Feature Specification: Install History Cleanup

**Feature Branch**: `030-install-history-cleanup`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User testing feedback (2026-11-13): (a) editing a still-installed part should offer a removed date/time and move the part to storage when one is entered; (b) the Delete button in install history has no border; (c) deleted parts should be labeled "(deleted)" in install history with a way to remove the entry, and deleting a part should by default remove its install history everywhere, with an option to keep it. The rider chose to always show a small confirmation when deleting a part.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End an Installation From the Edit Form (Priority: P1)

As the rider back-filling old data, I want to enter a removed date and time when editing a part that is still installed, so the part is recorded as taken off and moved to storage without a separate trip to the bike screen.

**Why this priority**: It lets the rider correct a part's history in one place, which is the heart of retroactive entry.

**Independent Test**: A chain is installed on a bike. Open its Install History, Edit the open period, enter a removed date a few days ago, Save: the period shows that removal, the chain is in storage, and its mileage counts only the rides up to that moment.

**Acceptance Scenarios**:

1. **Given** the edit form of a still-installed period, **When** it is shown, **Then** it includes optional "Removed on" and "Time (optional)" fields, blank, with a hint that filling them ends the installation and moves the part to storage.
2. **Given** a valid removed moment (after the install moment and not in the future in the rider's time zone), **When** the rider saves, **Then** the period is closed at that moment, the part is moved to storage with its own sub-parts, and the part's mileage is recalculated to count only rides within the installation.
3. **Given** the part has sub-parts installed in it, **When** it is moved to storage this way, **Then** they stay inside it and also leave the bike at that moment, each with their own installation closed at that moment.
4. **Given** the removed fields are left blank, **When** the rider saves, **Then** the part stays installed and only the install moment or place changes, as before.
5. **Given** a removed moment that is not after the install moment, or is in the future in the rider's zone, or is not a valid date or time, **When** the rider saves, **Then** the form is shown again with a clear message beside the field, and nothing changes (the part stays installed).
6. **Given** the edit form was opened from a bike's Install History, **When** the rider saves or cancels, **Then** they return to that bike's Install History; otherwise to the part's.
7. **Given** a period that is already closed, **When** it is edited, **Then** the form behaves as before (removed fields required).
8. **Given** the part is moved to storage this way, **When** the rider opens the bike's or the part's Install History, **Then** the row shows the removal moment and "Placed in" as before, and no maintenance entry is created.

---

### User Story 2 - Deleted Parts Are Labeled and Their Entries Removable (Priority: P1)

As the rider, I want rows for parts I have deleted to say "(deleted)" and to have a Delete button, so I can tell them apart and clear them out.

**Why this priority**: Today these rows have no buttons and no explanation, which is confusing.

**Independent Test**: Delete a part while keeping its history; on the bike's Install History its rows read "<name> (deleted)" with a Delete button; delete one: only that row disappears.

**Acceptance Scenarios**:

1. **Given** a bike's Install History, **When** a row is for a part that has been deleted, **Then** the part's name is followed by "(deleted)" and it is not a link.
2. **Given** such a row, **When** the rider chooses Delete, **Then** only that entry is removed and the rider returns to the bike's Install History; no other row, part or mileage is affected.
3. **Given** rows of deleted parts, **When** they are shown, **Then** they have no Edit button (the part no longer exists to edit).
4. **Given** the Delete button on any install history row (a part's or a bike's, including deleted parts), **When** it is shown, **Then** it has the same visible border as the Edit button beside it.
5. **Given** a row for a part that still exists and has been removed, **When** it is shown, **Then** it keeps Edit and Delete as before; a part that is still installed keeps only Edit.

---

### User Story 3 - Deleting a Part Removes Its Install History Unless Kept (Priority: P1)

As the rider, I want deleting a part to remove its install history from everywhere by default, with a choice to keep it, so deleted parts don't leave clutter but I can retain history when I want it.

**Why this priority**: It stops the leftover rows the rider found, and the keep option protects history the rider wants.

**Independent Test**: Delete a tire with the box unchecked: its rows are gone from the bike's Install History. Delete another with "Keep install history" checked: its rows remain, labeled "(deleted)".

**Acceptance Scenarios**:

1. **Given** the rider chooses to delete any part (Trash on a tree row, or the part's own Trash button), **When** the action is started, **Then** a short confirmation is always shown: what will be deleted, that its sub-parts (if any) move to storage, that maintenance history and schedules (if any) are deleted with it as before, and a **Keep install history** checkbox, unchecked, with Delete and Cancel buttons.
2. **Given** the confirmation with the box unchecked, **When** the rider confirms, **Then** the part is deleted and every install history entry of that part is removed, so it no longer appears in its own history, the bike's Install History, or anywhere else those entries were shown.
3. **Given** the confirmation with the box checked, **When** the rider confirms, **Then** the part is deleted and its install history entries are kept, shown as "(deleted)" in the bike's Install History, and removable later one by one (User Story 2).
4. **Given** the part being deleted has sub-parts, **When** it is deleted, **Then** the sub-parts move to storage as before and keep all of their own install history (only the deleted part's entries are affected).
5. **Given** Cancel, **When** it is chosen, **Then** nothing is deleted and the rider returns to the screen they were on.
6. **Given** deleting a bike, **When** it is deleted, **Then** this feature changes nothing (its parts move to storage and keep their history).
7. **Given** a part deleted before this feature, **When** its rows appear, **Then** they are labeled "(deleted)" and can be removed by hand.
8. **Given** the rider is not signed in, **When** any delete action is requested, **Then** sign-in is required.

---

### Edge Cases

- Entering a removed moment equal to the install moment is refused (the part would have no duration).
- A part moved to storage this way can be installed again later through the normal screens; its new installation is a separate period.
- The part's mileage after a retroactive removal counts only the rides during its installations; rides after the removal moment no longer count toward it.
- Deleting a deleted part's entry never changes any mileage (the part is gone).
- A part deleted without keeping its history has no rows left, so nothing shows as "(deleted)" for it.
- Confirming a delete twice (a double click) deletes the part once.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The edit form of a still-installed install period MUST offer optional removed date and time fields, blank by default.
- **FR-002**: When a valid removed moment is entered, the system MUST close the period at that moment, move the part (with its own sub-parts) to storage, close the sub-parts' installations at that moment, and recalculate the mileage of the part and its sub-parts; it MUST NOT create any maintenance entry.
- **FR-003**: A removed moment MUST be after the install moment and not in the future in the rider's chosen time zone; otherwise the system MUST show a clear message beside the field and change nothing.
- **FR-004**: Leaving the removed fields blank MUST leave the part installed, as before.
- **FR-005**: After saving or cancelling an edit opened from a bike's Install History, the rider MUST return to that bike's Install History.
- **FR-006**: Install history rows for parts that have been deleted MUST show "(deleted)" after the part's name (no link) and MUST offer Delete but not Edit.
- **FR-007**: Deleting an install history entry of a deleted part MUST remove only that entry.
- **FR-008**: The Delete button on every install history row MUST be drawn as a normal bordered button like the Edit button.
- **FR-009**: Starting a delete of any part MUST always show a short confirmation containing the consequences and an unchecked "Keep install history" checkbox, with Delete and Cancel.
- **FR-010**: Confirming with the checkbox unchecked MUST delete the part and all of its install history entries; confirming with it checked MUST delete the part and keep its entries (shown as "(deleted)").
- **FR-011**: Deleting a part MUST NOT remove the install history of its sub-parts, which are kept and moved to storage as before.
- **FR-012**: All of these actions MUST require sign-in.

### Key Entities

- **Installation period**: one stretch during which a part sat in one place on one bike (existing); closed by a removal moment. A part's install history is the set of its periods; the bike's and parents' views are built from the same periods.
- **Deleted part**: a part the rider deleted; its kept periods remain visible as "(deleted)" until removed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can end an installation with a past date and time in one edit (no more than one form submission).
- **SC-002**: After deleting a part with the box unchecked, 0 install history rows for it remain anywhere.
- **SC-003**: After deleting a part with the box checked, 100% of its rows remain, each labeled "(deleted)".
- **SC-004**: Every Delete button in install history shows a border.

## Assumptions

- "Move to storage, if possible" means the removed moment is valid as in FR-003; sub-parts stay inside the moved part.
- The always-shown confirmation replaces the earlier confirmation that appeared only when a part had sub-parts or maintenance history; it carries the same wording for those cases.
- Mileage is recalculated with the existing rules (rides within each installation period).
- The "Keep install history" default is unchecked, per the rider's wording.
- Times typed here are wall-clock times as elsewhere; the future check uses the rider's chosen time zone (feature 023).
