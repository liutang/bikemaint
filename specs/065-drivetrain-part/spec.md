# Feature Specification: Drivetrain Part

**Feature Branch**: `065-drivetrain-part`
**Created**: 2026-11-15
**Input**: User testing feedback: add a Drivetrain part under the Drivetrain section of the Add a part palette.

## User Scenarios & Testing
### User Story 1 - Add a Drivetrain Part (Priority: P1)
1. **Given** the Add a part palette or the Add part form, **Then** the Drivetrain category lists "Drivetrain" (after Derailleur, before Pedals) and it can be added anywhere like any part.
2. **Given** existing parts of kind drivetrain (older, hidden), **Then** they keep working unchanged.

## Requirements
- **FR-001**: The `drivetrain` kind (name "Drivetrain") MUST be offered in the Drivetrain category in alphabetical position; 35 kinds are offered.

## Success Criteria
- **SC-001**: The rider adds a Drivetrain part from the palette in one drag.

## Assumptions
- Same icon and rules as other parts; no migration (the kind id already exists).
