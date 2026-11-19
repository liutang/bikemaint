# Feature Specification: Sync Rules for Bikes and Parts

**Feature Branch**: `060-sync-rules`
**Created**: 2026-11-14
**Input**: User testing feedback: add synchronization rules to the bike and part Edit screens so the rider can filter which Strava activities sync with the bike or part, by Sport, Ride Type and Keywords. Clarified: rules live on both bikes and parts; a ride must match every filter that is filled in (blank = anything), keywords match any one; saving re-applies the rules to all existing Strava rides.

## User Scenarios & Testing

### User Story 1 - Keep Only the Rides That Belong (Priority: P1)
A rider sets a bike's rules (for example Sport: Ride and Gravel ride, Keywords: `commute`), saves, and the bike's mileage, rides and schedules count only matching Strava rides.

**Acceptance Scenarios**:
1. **Given** a bike's Edit screen, **Then** a Sync rules section offers Sport (checkboxes), Ride type (Default, Race, Workout) and Keywords (comma-separated text), and a Save rules button; empty means no filter.
2. **Given** rules with several filters, **Then** a Strava ride on that bike counts only if it matches every filled-in filter; for Keywords, one keyword found (any case) in the activity name is enough.
3. **Given** saved rules, **Then** all existing Strava rides on the bike are re-checked at once: rides that no longer match are left out of mileage, totals, the Rides list and schedules; rides that match again come back. Manual rides and rides the rider edited are never excluded.
4. **Given** a new sync, **Then** incoming Strava rides are filtered by the bike's rules the same way.
5. **Given** a part's Edit screen, **Then** the same section applies to the part: only rides matching the part's rules count toward that part's mileage (and its period and usage totals) while it is on a bike; the bike's own totals are unaffected.
6. **Given** a ride whose Strava details were never stored (rides imported before this feature), **Then** it is treated as matching until a Re-import stores the details, so nothing disappears silently.
7. **Given** unknown sports, ride types, or too long keywords, **Then** the save is refused with a message beside the field.

### Edge Cases
- Keywords match the activity name only (Strava's activity list does not include descriptions).
- A rule with nothing selected and no keywords is the same as no rule.
- Rule changes on a part never change another part.

## Requirements
- **FR-001**: Store per bike and per part a rule: sports (set), ride types (set), keywords (list). Sports are Strava's cycling sport types (Ride, Gravel ride, Mountain bike ride, E-bike ride, E-mountain bike ride, Virtual ride, Handcycle, Velomobile); ride types are Default, Race, Workout.
- **FR-002**: Strava sync and Re-import MUST store each ride's sport type, ride type and activity name.
- **FR-003**: A bike's rule MUST exclude non-matching, unedited Strava rides from everything that counts rides; a part's rule MUST exclude them from that part's mileage only.
- **FR-004**: Saving rules MUST re-apply them to existing rides and recompute affected mileage.
- **FR-005**: Routes `POST /bikes/{id}/sync-rules` and `POST /components/{id}/sync-rules` validate, save, and return to the item's Edit screen; sign-in required; 404 unknown.
- **FR-006**: Rides with unknown details MUST match.

## Success Criteria
- **SC-001**: After saving "Race only", the bike's mileage equals the sum of its race rides (plus manual and edited rides and baseline).

## Assumptions
- Applies to Strava rides only.
- No automatic re-import; the rider uses Re-import to fill details of older rides.

## Amendments

- **2026-11-18 (feature 083)**: the stored Strava `activity_name` and `sport_type` are shown as the ride's title and type and are read-only in the app; Re-import fills them on edited rides when missing. Manual rides store their title in `activity_name` but still always match (they are user-modified). See `specs/083-rides-title-type/`.
