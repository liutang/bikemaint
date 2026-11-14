# Feature Specification: Maintenance Mileage From Ride History

**Feature Branch**: `038-maintenance-mileage-at-date`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: when logging maintenance, auto-calculate the mileage from the date and time of the maintenance and the ride history of the bike or part. (Today a blank mileage means the item's current total, which is wrong for maintenance logged after the fact.) Changes feature 001's "blank = current total" rule, so it is specified as its own feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mileage at Service Follows the Date Performed (Priority: P1)

When the rider logs maintenance and leaves "Mileage at service" blank, the system fills it in with the mileage the bike or part had at the date and time performed, counting only the rides up to that moment.

**Why this priority**: Backdated maintenance (back-filling old data) currently records today's total, so due dates and the next cycle's baseline are wrong.

**Independent Test**: Give a bike a baseline of 100 and rides of 10 (March), 20 (April), 30 (May). Log maintenance dated April 15 with blank mileage: it records 130.

**Acceptance Scenarios**:

1. **Given** a bike with rides before and after the date performed, **When** maintenance is logged with blank mileage, **Then** the recorded mileage is the baseline plus all rides at or before the date and time performed (and adjustments), excluding later rides.
2. **Given** a part that was installed for only part of that time, **When** maintenance is logged with blank mileage, **Then** the part's mileage counts only rides while it was installed on a bike, up to the date and time performed, plus its baseline.
3. **Given** the time performed is blank, **When** the mileage is calculated, **Then** it counts rides through the end of that day.
4. **Given** the date performed is today or later than the last ride, **When** blank, **Then** the result equals the item's current total.
5. **Given** a typed mileage, **When** maintenance is logged, **Then** the typed value is recorded unchanged.
6. **Given** the Log maintenance form, **When** it opens, **Then** the hint says the mileage is calculated from the ride history up to the date and time performed when left blank.
7. **Given** a ride that was deleted by the rider or upstream, **When** the mileage is calculated, **Then** it is not counted.

### Edge Cases

- Editing an entry with the mileage field blank keeps the entry's existing mileage (unchanged behavior).
- Manual adjustments are counted in full (they carry no effective date).
- Dates before the first ride give just the baseline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Logging maintenance with a blank mileage MUST record the item's mileage as of the date and time performed: baseline, plus live rides up to that moment (for a part, only rides during its installation periods), plus manual adjustments.
- **FR-002**: A blank time performed MUST count the whole day.
- **FR-003**: A typed mileage MUST be recorded as typed.
- **FR-004**: The form hint MUST describe the calculation; it MUST no longer promise the current total.
- **FR-005**: Completing a schedule item (which logs maintenance dated now) MUST keep recording the current total.

### Key Entities

- **Maintenance entry**: unchanged; only how its default mileage is derived changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Maintenance logged for a past date with blank mileage never counts a ride that happened after that date.
- **SC-002**: Maintenance logged for today with blank mileage matches the item's current total.

## Assumptions

- Ride times are compared as stored, as installation periods already are.
- Applies to logging only, not editing.
