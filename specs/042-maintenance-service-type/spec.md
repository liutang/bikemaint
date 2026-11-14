# Feature Specification: Maintenance Service Type

**Feature Branch**: `042-maintenance-service-type`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: "The manual log maintenance screen still has Description. That should be Service Type instead, to match the maintenance schedule and it should also contain the same drop-down items." Builds on 040 (service types).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log Maintenance by Service Type (Priority: P1)

The Log maintenance form (bike or part) has a "Service type" drop-down (Charge, Check, Clean, Lube/Wax, Replace, Service, Topup) where the free-text Description was. The history list shows a "Service type" column.

**Independent Test**: Log "Lube/Wax" on a bike; the history shows it under Service type.

**Acceptance Scenarios**:

1. **Given** the Log maintenance form, **When** it opens, **Then** it has a required Service type drop-down with exactly the seven types and no Description field.
2. **Given** a valid type, date and optional time and mileage, **When** saved, **Then** the entry records that service type and appears in the history.
3. **Given** no type or a type outside the list, **When** saved, **Then** the form re-opens with a message beside the field and nothing is saved.
4. **Given** the history list, **When** shown, **Then** the column is titled Service type.
5. **Given** an entry logged before this feature with free-text wording, **When** it is shown, **Then** the old wording is displayed unchanged; **when** it is opened for Edit, **then** the drop-down is empty and required, with a note to choose a type, and saving converts it.
6. **Given** an entry created by marking a schedule done, **When** shown, **Then** its service type is the schedule's service type.

### Edge Cases

- Existing entries are never rewritten automatically.
- Mileage and date behavior (038) is unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Log and Edit maintenance MUST take a service type from the fixed list instead of free text, validated at the boundary.
- **FR-002**: The entry MUST store the service type as its text (the existing column), so history, schedules and exports are unchanged.
- **FR-003**: Older free-text entries MUST display unchanged and MUST require choosing a type when edited.

### Key Entities

- **Maintenance entry**: its description is now one of the service types for entries logged or edited from now on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every entry logged after this feature has one of the seven service types.

## Assumptions

- Entries created before this feature are left as they are until the rider edits them.
