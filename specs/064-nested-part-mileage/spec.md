# Feature Specification: A Part Earns Its Parents' Miles

**Feature Branch**: `064-nested-part-mileage`
**Created**: 2026-11-15
**Input**: User testing feedback: a tire logged inside a wheelset (the wheelset was in storage when the tire was added) shows 0 miles although the wheelset was on the bike during that time. Miles for parts should accumulate their parents' miles.

## User Scenarios & Testing

### User Story 1 - Tire Inherits the Wheelset's Bike Time (Priority: P1)
**Acceptance Scenarios**:
1. **Given** a wheelset on bike B from 2020-10-08 to 2023-01-23 and a tire logged inside the wheelset from 2022-06-22 to 2023-01-23, **Then** the tire's miles are the rides on B in that overlap.
2. **Given** the tire's window only partly overlaps the wheelset's time on a bike, **Then** only the overlap counts; time the wheelset was in storage counts nothing.
3. **Given** deeper nesting (tire in rim in wheelset on a bike), **Then** the bike time comes from the nearest ancestors recursively.
4. **Given** Log/Edit a period with an Inside part chosen, **Then** the bike field is ignored (the bike is whichever bike that part was on at the time) and the form says so; with no Inside part the chosen bike is used as before.
5. **Given** a period inside a part, **Then** the period's Miles, its Rides list, the part's total, usage schedules (rides/hours) and "mileage at service" all use the same derived rides, each ride counted once.
6. **Given** a parent's period is added, edited or deleted, **Then** the totals of the parts inside it are recomputed.

### Edge Cases
- A parent never on a bike during the window gives 0.
- A part's own sync rule still applies.

## Requirements
- **FR-001**: A period with a parent part and no bike of its own counts rides on the bikes the parent (recursively) was on, limited to the overlap of the time ranges; a period with its own bike counts as before.
- **FR-002**: Logging or editing a closed period with an Inside part MUST store no bike of its own.
- **FR-003**: Every place that totals or lists rides for a part or period MUST use the same rule.
- **FR-004**: Parent period changes recompute dependent parts' totals.

## Success Criteria
- **SC-001**: The tire from the report shows the same miles as the wheelset over the overlapping dates.

## Assumptions
- Bike Install History lists only periods that name a bike directly.
