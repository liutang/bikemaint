# Feature Specification: Strava Maintenance Actions Live in Bike Edit

**Feature Branch**: `057-strava-actions-in-edit`
**Created**: 2026-11-14
**Input**: User testing feedback: Re-import Strava history and Unpair from Strava are rarely used and do not belong on the bike's main screen; move them into the bike's Edit screen.

## User Scenarios & Testing

### User Story 1 - A Cleaner Bike Screen (Priority: P1)
**Acceptance Scenarios**:
1. **Given** a bike paired with Strava, **Then** its main screen's actions row has no Re-import Strava history or Unpair from Strava button.
2. **Given** the same bike's Edit screen, **Then** a Strava section shows both buttons (bordered), working as before (017).
3. **Given** a bike not paired, **Then** Pair with Strava stays on its main screen and the Edit screen has no Strava section.

## Requirements
- **FR-001**: The two buttons MUST be removed from the bike screen and offered on `/bikes/{id}/edit` for paired bikes only, with the same routes and behavior (017 FR-006 to FR-015).
- **FR-002**: Pair with Strava is unchanged.

## Success Criteria
- **SC-001**: The bike screen's action row has only commonly used actions.

## Assumptions
- After Re-import or Unpair the rider returns to the bike screen, as before.
