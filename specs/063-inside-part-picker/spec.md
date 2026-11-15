# Feature Specification: Pick the Part a Period Was Inside

**Feature Branch**: `063-inside-part-picker`
**Created**: 2026-11-15
**Input**: User testing feedback: on Log a period, "Inside part (optional)" asks for a part number, but part numbers are not shown anywhere, so there is no way to know it (amends specs/015).

## User Scenarios & Testing

### User Story 1 - Choose the Part by Name (Priority: P1)
**Acceptance Scenarios**:
1. **Given** the Log a period or Edit period form, **Then** "Inside part (optional)" is a list: first "None (on the bike or frame)", then every live part by name and kind, never the part itself.
2. **Given** a part chosen, **Then** saving stores it exactly as the number did before (same validation and mileage).
3. **Given** Edit period for a period inside a part, **Then** that part is preselected; if that part was deleted it is still listed, marked "(deleted)", so saving does not silently drop it.
4. **Given** two parts with the same name and kind, **Then** their entries are told apart (a number suffix).
5. **Given** a refused form, **Then** the choice is kept.

### Edge Cases
- Typed numbers are no longer needed; a posted numeric id still works (the contract of the field is unchanged).

## Requirements
- **FR-001**: The Inside part field MUST be a select built by `component_history_service.parent_options(component_id, current_parent_id)`.
- **FR-002**: The hint MUST say to pick the part it was mounted in, for example the wheel, and to leave it on None for the frame or bike.

## Success Criteria
- **SC-001**: A rider logs a tire period inside a wheelset without knowing any part number.

## Assumptions
- The bike field stays: the rider names the bike; mileage uses it (see the Rides button on the period to see which rides count).
