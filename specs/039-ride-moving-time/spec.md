# Feature Specification: Ride Moving Time

**Feature Branch**: `039-ride-moving-time`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: maintenance schedules need to be settable by Hours of use, and the app records no ride time today. The rider chose to store Strava moving time on rides (re-import fills old ones) and add an optional duration to manual rides. This feature records and shows ride time; the schedule feature (040) uses it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Strava Rides Carry Their Moving Time (Priority: P1)

Every ride imported or synced from Strava keeps its moving time. Re-importing a bike's history fills in the time on rides imported before this feature.

**Independent Test**: Sync an activity with a moving time of 5400 seconds and see 1:30 in the Rides list; re-import fills an older ride.

**Acceptance Scenarios**:

1. **Given** a Strava activity with a moving time, **When** it is synced, **Then** the ride stores it and the Rides list shows it as `h:mm` (for example `1:30`).
2. **Given** a ride imported before this feature (no time), **When** the bike's history is re-imported, **Then** the ride gains its moving time and nothing else about it changes.
3. **Given** a ride the rider edited or deleted, **When** Strava sync runs, **Then** it is not overwritten (unchanged rule).
4. **Given** a ride with no time, **When** the list is shown, **Then** the time column is blank (not `0:00`).

---

### User Story 2 - Add or Edit a Duration on a Manual Ride (Priority: P1)

The Add a ride and Edit ride forms have an optional "Moving time (h:mm)" field. Blank means unknown.

**Acceptance Scenarios**:

1. **Given** the Add a ride form, **When** it opens, **Then** it offers an optional "Moving time" field with the format hint `h:mm`.
2. **Given** `1:30` is entered, **When** saved, **Then** the ride stores 5400 seconds and the list shows `1:30`.
3. **Given** the field holds something that is not `h:mm` (for example `abc`, `1:75`, `0:00`), **When** saved, **Then** the form re-opens with a message beside the field and nothing is saved.
4. **Given** an existing ride, **When** edited, **Then** the field shows its current time and a changed or cleared value is saved.

### Edge Cases

- Times over 99 hours are refused; zero is refused (leave it blank instead).
- A part's read-only ride log shows the same time column.
- Totals, mileage and every other column are unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each ride MUST be able to store a moving time in whole seconds, unknown by default.
- **FR-002**: Strava sync and re-import MUST store the activity's moving time on the ride, subject to the existing rule that edited or deleted rides are never overwritten.
- **FR-003**: Add and Edit ride MUST accept an optional `h:mm` moving time, validated at the boundary (1 minute to 99:59); blank means unknown.
- **FR-004**: The Rides list (bike and part) MUST show a "Moving time" column in `h:mm`, blank when unknown.

### Key Entities

- **Ride**: gains an optional moving time (seconds).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a re-import, every Strava ride that Strava reports a moving time for shows it.
- **SC-002**: A manual ride entered with `1:30` shows `1:30` and counts as 5400 seconds.

## Assumptions

- Moving time (not elapsed time) is what counts as time on the bike.
- Rides imported before this feature stay blank until re-imported.
