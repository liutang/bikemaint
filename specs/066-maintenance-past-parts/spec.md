# Feature Specification: Maintenance History Includes Past Parts

**Feature Branch**: `066-maintenance-past-parts`
**Created**: 2026-11-15
**Input**: User testing feedback: like install history, the maintenance history of a bike or part should surface the history of its attached parts, recursively. Clarified: also parts that were attached at the time but are removed now.

## User Scenarios & Testing
### User Story 1 - See Maintenance Done While a Part Was Attached (Priority: P1)
1. **Given** a bike, **Then** its maintenance history also lists entries of parts that were on it at the time of the entry (an install period on the bike, directly or inside a part that was on it), even if the part is removed or deleted since, in addition to the currently attached parts (as today).
2. **Given** a part, **Then** its history also lists entries of parts that were inside it at the time (directly or through deeper parts), even if removed since.
3. **Given** an entry of a part dated outside every window it was attached under this bike or part, **Then** it is not listed there.
4. **Given** such rows, **Then** they use the Part column (link to the part's history, or its name when deleted) and have no Edit or Delete here; each entry appears once.

### Edge Cases
- A blank entry time counts as the end of that day; windows end exclusive.
- Same wall clock rule as the Rides comparison (typed times as typed).

## Requirements
- **FR-001**: `maintenance_service.list_for_bike_rows` and `list_for_component_tree` MUST add past-attached parts' entries by the rule above, without duplicates.
- **FR-002**: Windows come from install periods (bike windows as in specs/064; part-inside windows recursively by overlap).

## Success Criteria
- **SC-001**: A chain's lube logged last year shows in the bike's history after the chain is removed, and not for entries dated after the removal.
