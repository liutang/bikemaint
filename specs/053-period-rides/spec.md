# Feature Specification: Rides for an Install Period

**Feature Branch**: `053-period-rides`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback: for each install history period, add a Rides button that links to a filtered list of rides corresponding to that part's install period.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Which Rides Count Toward a Period (Priority: P1)

On a part's Install History and on a bike's Install History, each period row has a Rides button next to Edit and Delete. It opens the rides that count toward that one period, so the rider can check the period's Miles against their ride history.

**Independent Test**: Install a part on a bike for a period covering three of the bike's four rides; open that period's Rides; exactly those three rides are listed and their total equals the period's Miles.

**Acceptance Scenarios**:

1. **Given** a part's Install History, **When** it opens, **Then** each period row has a Rides button.
2. **Given** a bike's Install History, **When** it opens, **Then** each period row has a Rides button, including rows of parts since deleted.
3. **Given** a period, **When** Rides is chosen, **Then** a read-only list shows the rides on that period's bike that started at or after the install moment and before the removal moment (no end when still installed), compared as in 015 FR-013.
4. **Given** the list, **When** shown, **Then** it uses the Rides log columns (Date & time, Miles, Moving time, Source, Note, Total) with no Starting mileage row and no adjustments; each row's Total is the running sum of the listed rides, and the header total equals the period's Miles on the part's Install History.
5. **Given** the list, **When** shown, **Then** the title names the part and the period (bike or place, installed and removed times in the clock setting), and the breadcrumb leads back to the install history.
6. **Given** a period with no rides, **When** Rides is chosen, **Then** an empty state says no rides counted in that period.
7. **Given** an unknown period or a signed-out visitor, **When** the route is requested, **Then** it answers 404 or redirects to login respectively.

### Edge Cases

- A ride the rider deleted, or Strava deleted, is not listed (as in mileage).
- A ride that started before the install moment but ended after it is not listed (it counts by start time).
- A part that was placed inside another part: the period's bike is still the bike whose rides count.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each period row on a part's Install History and a bike's Install History MUST offer a Rides button linking to `/install-periods/{id}/rides`.
- **FR-002**: That page MUST list, oldest to newest running totals and newest first, the live rides on the period's bike inside the period, using the 015 FR-013 clock rule, read-only.
- **FR-003**: It MUST show no Starting mileage row and no adjustments; its total MUST equal the sum of the listed rides (the period's Miles).
- **FR-004**: The title MUST name the part and the period; the breadcrumb MUST lead back to the owning install history.
- **FR-005**: The route MUST require sign-in and answer 404 for an unknown period.

## Success Criteria *(mandatory)*

- **SC-001**: The total on a period's Rides page equals that period's Miles on the part's Install History in every case.
- **SC-002**: A rider can reach a period's rides in one click from either Install History screen.

## Assumptions

- Read-only: rides are edited from the bike's Rides screen.
- No new setting, table or migration.
