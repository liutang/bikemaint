# Feature Specification: Component Maintenance History Includes Attached Parts

**Feature Branch**: `048-component-history-tree`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User testing feedback: the service history of a component should include its own records and those of the parts attached to it, recursively. Attached parts' records are not editable; they link to that part's service history. Add a Part column between Date & time and Service type: "This part" for the component's own records, otherwise the attached part's name as a link.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the Whole Assembly's Service History (Priority: P1)

Opening a part's Maintenance history (for example a wheel) lists its own entries together with the entries of every part currently attached to it at any depth (rim, tire, spokes and so on), latest first.

**Independent Test**: Log a service on a wheel and one on its tire; the wheel's history shows both, the tire's row linked and read-only.

**Acceptance Scenarios**:

1. **Given** a part with attached parts (any depth), **When** its Maintenance history opens, **Then** it lists the part's own entries and all attached parts' entries, ordered by date and time performed, latest first.
2. **Given** the list, **When** shown, **Then** it has a Part column between Date & time and Service type.
3. **Given** a row for the part itself, **When** shown, **Then** Part reads "This part" and Edit and Delete are offered.
4. **Given** a row for an attached part, **When** shown, **Then** Part is that part's name as a link to the attached part's Maintenance history, and the row has no Edit or Delete; its Actions cell shows nothing (the link is the way in).
5. **Given** a part with no attached parts, **When** its history opens, **Then** only its own entries appear, all marked "This part".
6. **Given** an attached part is later moved off, trashed or stored elsewhere, **When** the history opens, **Then** its entries no longer appear here (only parts currently attached count).
7. **Given** the part has no entries at all (own or attached), **When** it opens, **Then** the empty state is shown as today.

### Edge Cases

- A bike's Maintenance history is unchanged by this feature (its own entries only, no Part column).
- Mileage-at-service of an attached part's entry is shown as recorded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A part's Maintenance history MUST include the entries of its currently attached parts at any depth, in the same date-and-time-descending order.
- **FR-002**: The part's history MUST show a Part column between Date & time and Service type: "This part", or the attached part's name linking to `/components/{id}/maintenance`.
- **FR-003**: Entries of attached parts MUST NOT offer Edit or Delete on that screen.

### Key Entities

- None new.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every entry of every currently attached part appears exactly once on the ancestor's history.
- **SC-002**: No attached part's entry on that screen has an Edit or Delete control.

## Assumptions

- "Attached" means currently installed in the part's sub-tree (not parts that used to be attached).
