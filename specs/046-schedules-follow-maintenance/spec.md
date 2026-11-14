# Feature Specification: Schedules Follow Logged Maintenance

**Feature Branch**: `046-schedules-follow-maintenance`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User testing feedback: a schedule showed a Topup 1048 days late; the rider then logged another Topup (2/23/2024) and the overdue card did not update. "Whenever something about a bike/part changes (usage gets logged, maintenance item added), any maintenance schedule items related to that bike/part should be recalculated." Amends 040 FR-011.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Logging Maintenance Resets the Matching Schedule (Priority: P1)

Logging (or editing) a maintenance entry of a service type on a bike or part restarts counting for that owner's schedules of the same type, so the board and notifications reflect it at once.

**Independent Test**: With an overdue "Topup every 4 months" on a wheel, log a Topup dated more recently; the schedule's next due date moves out and the overdue card updates.

**Acceptance Scenarios**:

1. **Given** an active schedule of a service type on a bike or part, **When** a maintenance entry of that type is logged on that same bike or part and is more recent than the schedule's current starting point, **Then** the schedule counts from that entry (its date and time, recorded mileage, and the rides and hours after it) and starts a new cycle, so due-soon notifications can fire again.
2. **Given** the entry is older than the schedule's starting point, **When** logged, **Then** nothing changes.
3. **Given** an entry of a different service type, or on a different bike or part, **When** logged, **Then** the schedule is not affected.
4. **Given** an existing matching entry is edited to a date more recent than the schedule's starting point, **When** saved, **Then** the schedule counts from it (no new cycle).
5. **Given** a schedule completed with Mark done, **When** it logs its own entry, **Then** the schedule is restarted once (not twice) as today.
6. **Given** usage is logged (rides added, synced or edited), **When** the board is opened, **Then** usage-based schedules already reflect it, because remaining usage is calculated each time the page is built.

### Edge Cases

- Deleting an entry does not move a schedule back.
- Schedules of other kinds of owner are untouched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Logging a maintenance entry MUST restart (count from the entry, new cycle) every active schedule on the same bike or part with the same service type whose starting point is earlier than the entry, except for the entry a schedule's own completion creates.
- **FR-002**: Editing an entry MUST re-base such schedules the same way without starting a new cycle.
- **FR-003**: Projections and the board MUST continue to be computed on read so usage changes always show.

### Key Entities

- **Schedule**: its starting point (baseline date, mileage, moment) and cycle may be updated by logging maintenance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After logging a more recent matching service, the schedule's next due date is never earlier than that service plus the interval.

## Assumptions

- "Same service type" is the entry's service type equal to the schedule's.
