# Feature Specification: Exact Mile Conversion

**Feature Branch**: `081-exact-mile-conversion`
**Created**: 2026-11-18
**Status**: Draft (queued by the rider on 2026-11-18; not yet approved for planning)
**Input**: Asked by the rider on 2026-11-18, "Would data conversion be seamless?", then "Add it to the next batch. I don't have archived bikes. I'm ok with old backups being off." Confirmed in the batch review: edited Strava rides are not rescaled, and recorded maintenance mileage stays as it is.

## Background

- **What Strava sends:** `distance` in meters, usually to the tenth of a meter.
- **What the app does:** it divides by 1,609.34 to get miles. A mile is exactly 1,609.344 meters, so every Strava ride reads about 0.00025% long: 0.025 mi per 10,000 mi.
- **Why fix it:** the rider wants totals to match Strava's exactly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Strava rides use the exact mile (Priority: P1)

**Why this priority**: It stops the error growing.

**Independent Test**: Sync an activity of 16,093.44 m. It is stored as exactly 10.0 mi.

**Acceptance Scenarios**:

1. **Given** any Strava activity, **When** it is synced or re-imported, **Then** its miles are its meters divided by 1,609.344.

---

### User Story 2 - Rides already synced are corrected once (Priority: P1)

**Why this priority**: Without it, old and new rides would use different miles.

**Independent Test**: A database holding a Strava ride stored as 16093.44 / 1609.34 mi is started on the update. The ride becomes 16093.44 / 1609.344 mi, the bike and part totals follow, and a second start changes nothing.

**Acceptance Scenarios**:

1. **Given** a Strava ride you haven't edited, **When** the update first starts, **Then** its miles are multiplied by 1,609.34 ÷ 1,609.344. That recovers Strava's meters and re-divides them exactly.
   - This includes rides left out by sync rules, rides you deleted, and rides on archived bikes.
2. **Given** a manual ride, or a Strava ride you edited, **Then** it is not changed. You may have typed its miles.
3. **Given** the update has run, **Then** bike and part totals are recomputed, and the correction is recorded so it never runs again.
4. **Given** values typed in miles (baseline mileage, mileage adjustments, maintenance entries' mileage at service), **Then** they are not changed.

### Edge Cases

- **Recorded maintenance mileage:** a mileage at service recorded before the update stays as recorded. It may read up to 0.025 mi per 10,000 mi lower than the same moment recomputed afterwards, which is invisible at one decimal place.
- **Old backups:** restoring a backup taken before the update brings back its old values. The backup format is not changed (the rider accepted this). A Re-import of each paired bike corrects their unedited Strava rides again.
- **Displayed totals** may move by 0.1 mi where rounding tips over.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Strava distances MUST be converted with 1,609.344 meters per mile.
- **FR-002**: A one-time step MUST rescale the miles of every Strava ride not edited by the rider by 1,609.34 ÷ 1,609.344. It is recorded as done, and totals are recomputed.
- **FR-003**: Manual rides, edited Strava rides, and every value typed in miles MUST NOT change.
- **FR-004**: The step MUST make no database copy and change no backup format.

### Key Entities

- **Ride miles**: `ride_activity.distance_miles`. For an unedited Strava ride it is always Strava's meters ÷ 1,609.344.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the update, every unedited Strava ride's miles × 1,609.344 equals its Strava meters to within floating-point precision.
- **SC-002**: Manual and edited rides are byte-for-byte unchanged.
- **SC-003**: A second start changes nothing.

## Assumptions

- **No archived bikes today:** the rider has none, but the step covers any that exist when it runs, since it doesn't go through Strava's upsert guard.
- **The constant's home:** it stays in `sync_service`.
- **Amends:** 001, where Strava distance conversion is described.
