# Feature Specification: Safe Bike Delete

**Feature Branch**: `029-safe-bike-delete`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User testing feedback (2026-11-13): "Delete this bike" is too prominent on the bike's main screen. Move it to the Edit screen and make the rider go through extra steps: type the bike's full name (for example "2023 Trek Madone") before the confirm button becomes active.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete a Bike Only on Purpose (Priority: P1)

As the rider, I want deleting a bike to be tucked away on the Edit screen and to require typing the bike's full name, so I can never delete a bike by a stray click.

**Why this priority**: Deleting a bike is the most destructive thing on its screen, and today it sits one click away on the main page.

**Independent Test**: Open "2023 Trek Madone". There is no delete control on its main screen. Open Edit: a separate delete area asks for the name; the Delete button is greyed out until "2023 Trek Madone" is typed exactly; then it works and returns to the garage with the bike gone and its parts in storage.

**Acceptance Scenarios**:

1. **Given** a bike's main screen, **When** it is shown, **Then** it has no "Delete this bike" section and no delete button.
2. **Given** the bike's Edit screen, **When** it is shown, **Then** below the edit form is a separate, clearly marked delete area ("Delete this bike") explaining what will happen and asking the rider to type the bike's full name exactly as shown (for example `2023 Trek Madone`).
3. **Given** the delete area, **When** the typed text is empty or does not match the bike's name exactly (different spelling, case, spacing, or extra characters), **Then** the Delete button is greyed out and cannot be used.
4. **Given** the delete area, **When** the typed text matches the bike's full name exactly, **Then** the Delete button becomes usable.
5. **Given** the Delete button is used with the exact name, **When** the bike is deleted, **Then** the rider returns to the garage, the bike is gone, its parts have moved to storage with their own sub-parts, and its rides and history are handled as they were before this change.
6. **Given** a request to delete that arrives without the exact name (for example from a stale page or another tool), **When** the server receives it, **Then** nothing is deleted and the Edit screen is shown again with a message beside the name field saying to type the bike's full name exactly.
7. **Given** the delete area, **When** it explains the consequences, **Then** it says the bike will be deleted, its parts will move to storage with their own sub-parts, and that this cannot be undone.
8. **Given** a bike whose name contains punctuation or spaces (for example `2023 Trek Madone SLR (Disc) 7.0`), **When** the rider types it exactly, **Then** the Delete button becomes usable; typing anything else keeps it unusable.
9. **Given** the rider is not signed in, **When** the delete action is requested, **Then** sign-in is required, as for every route.
10. **Given** a bike with no parts, history or schedules, **When** the rider deletes it, **Then** the same typed-name step applies (no exception for empty bikes).

---

### Edge Cases

- Leading or trailing spaces in the typed text do not count as a match; the name must match exactly.
- The match is against the bike's name as currently saved; if the rider edits the name first and saves, the new name is the one to type.
- Deleting a part is unchanged by this feature.
- The earlier "are you sure" confirmation step for bikes (shown when a bike had parts or history) is replaced by the typed-name step; it is not shown in addition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bike's main screen MUST NOT offer any way to delete the bike.
- **FR-002**: The bike's Edit screen MUST contain a separate, clearly marked delete area that states the consequences and asks the rider to type the bike's full name exactly as shown.
- **FR-003**: The delete button MUST be greyed out and unusable until the typed text equals the bike's full name exactly, and usable when it does.
- **FR-004**: The server MUST refuse to delete a bike unless the submitted name equals the bike's current name exactly, showing the Edit screen again with a message beside the name field; nothing is deleted in that case.
- **FR-005**: A successful delete MUST behave as before (bike deleted; its parts moved to storage with their sub-parts) and MUST send the rider to the garage.
- **FR-006**: The typed-name step MUST apply to every bike, whether or not it has parts, history or schedules, and MUST replace the earlier confirmation step for bikes.
- **FR-007**: The delete action MUST require sign-in.

### Key Entities

- **Bike**: unchanged. Its full name (as shown on its screens) is the confirmation phrase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bike cannot be deleted with fewer than two deliberate steps beyond opening it (open Edit, then type its name).
- **SC-002**: 100% of delete requests without the exact name leave the bike untouched.
- **SC-003**: The bike's main screen has 0 delete controls.

## Assumptions

- The greyed-out behavior needs no script: the browser's own form checking compares the typed text with the name, and the page styles the button as unavailable until it matches. The server check is the authority.
- The confirmation phrase is the bike's name exactly as displayed, case-sensitive.
- Deleting a part, ride or history entry is out of scope.
