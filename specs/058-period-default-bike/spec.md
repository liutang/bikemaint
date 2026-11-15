# Feature Specification: Default Bike When Logging a Period

**Feature Branch**: `058-period-default-bike`
**Created**: 2026-11-14
**Input**: User testing feedback: when logging a period in a part's Install history, default the bike to the bike the part is currently installed on, or else the bike of the next most recent install period.

## User Scenarios & Testing

### User Story 1 - The Right Bike Is Already Chosen (Priority: P1)
**Acceptance Scenarios**:
1. **Given** a part installed on a bike (directly or inside another part), **When** the Log a period form opens, **Then** that bike is preselected.
2. **Given** a part in storage with past periods, **Then** the bike of its most recent period (latest installed time) is preselected.
3. **Given** a part with no periods and not installed, **Then** no bike is preselected beyond the list's first entry, as today.
4. **Given** the form re-shown after a validation error, **Then** the rider's own choice is kept.
5. **Given** editing an existing period, **Then** its own bike is shown, as today.

## Requirements
- **FR-001**: The part's new-period form MUST preselect, in order: the bike the part is installed on (resolving through parent parts), else the bike of its most recent period by install time, if that bike still exists.
- **FR-002**: The bike-side log form and the edit form are unchanged.

## Success Criteria
- **SC-001**: In the common case (logging history for a part on a bike) the rider does not need to change the bike field.

## Assumptions
- A deleted bike is never preselected.
