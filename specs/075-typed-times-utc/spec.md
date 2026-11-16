# Feature Specification: Store Typed Times in UTC

**Feature Branch**: `075-typed-times-utc`
**Created**: 2026-11-16
**Status**: Draft (spec requested by the rider; not approved to build)
**Input**: "Type my time in local time, use timezone setting to record the time as UTC in the DB to match Strava. Then convert back to local time for display purposes." For example, a manual ride typed as 5:39 PM with the zone set to New York (EST) is recorded as 10:39 PM UTC. It is then shown as 5:39 PM EST, the same way Strava rides are shown.

## Background

Today the app keeps two kinds of time:

- **Recorded instants**: Strava rides, completed tasks, "now" install times. These are UTC, shown in the saved zone with its abbreviation, for example `2026-11-13 2:26PM EST`.
- **Typed times**: manual rides, install and removal dates on Install History, and maintenance entry dates and times. These are stored exactly as typed, with no zone, and shown without an abbreviation, for example `2026-11-16 5:00PM`.

Because of this, the Rides list mixes labelled and unlabelled times, and the app needs special rules (015 FR-013, 049, 051) to compare the two kinds. Editing a Strava ride's time also prefills the form with the UTC clock time, not the local one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed times are recorded like Strava times (Priority: P1)

The rider types a time in local time. The app records it as a UTC instant using the saved zone, and shows it back in local time with the zone's abbreviation, like every Strava ride.

**Why this priority**: It is the request. One kind of time everywhere means one display rule and one comparison rule.

**Independent Test**: With the zone set to New York, add a manual ride at 2026-11-16 5:39 PM. It is stored as `2026-11-16T22:39` UTC and listed as `2026-11-16 5:39PM EST`, in the same format as the Strava rows.

**Acceptance Scenarios**:

1. **Given** the zone is New York, **When** the rider adds a manual ride on 2026-11-16 at 5:39 PM, **Then** it is recorded as 22:39 UTC and listed as `2026-11-16 5:39PM EST`.
2. **Given** a summer date, **When** the rider types 2026-07-04 at 9:00 AM, **Then** it is recorded as 13:00 UTC (EDT is UTC-4) and listed as `2026-07-04 9:00AM EDT`. Each date uses the offset in force on that date.
3. **Given** a manual ride with no time, **Then** it counts as noon on that date in the saved zone, as today, recorded in UTC.
4. **Given** any typed time, **When** the rider opens its Edit form, **Then** the date and time fields show the local time they typed. Saving without changes records the same instant.
5. **Given** a Strava ride, **When** the rider opens its Edit form, **Then** the time field shows its local time (today it shows UTC).
6. **The same rule applies to every place a time is typed:**
   - manual rides and ride edits;
   - install and removal moments on a part's or a bike's Install History (Log and Edit period);
   - the install date given when adding a part;
   - maintenance entries that have a time (Log and Edit maintenance).
7. **Given** a stored time, **Then** it is shown everywhere as `date time ABBR` in the saved zone and clock format. This covers the Rides list, Install History and Maintenance history.

---

### User Story 2 - Existing typed times are converted once (Priority: P1)

**Acceptance Scenarios**:

1. **Given** existing typed times, **When** the app is updated, **Then** each one is converted once to UTC, using the saved zone and the offset in force on its own date. A manual ride typed as 2026-11-16 5:00 PM becomes 22:00 UTC and still reads `2026-11-16 5:00PM EST`.
2. **Given** the update has run, **Then** every bike's and part's mileage, every period's Miles and Rides, every maintenance entry's history placement and every schedule's progress are the same as before.
3. **Given** a backup file made before this change, **When** it is restored, **Then** its typed times are converted using the zone saved in that backup.

---

### User Story 3 - Changing the zone later (Priority: P2)

**Acceptance Scenarios**:

1. **Given** typed times were recorded in New York, **When** the rider changes the zone to Los Angeles, **Then** every time is shown in Los Angeles time, three hours earlier, with PST or PDT. This includes manual rides, install moments and maintenance times. Strava rides behave this way today.
2. **Given** a zone change, **Then** nothing stored changes, and mileage and period totals stay the same.

### Edge Cases

- **A time that doesn't exist** (2:30 AM on the spring-forward day): it is read with the offset in force before the change, so it is recorded as 3:30 AM daylight time and shown that way.
- **A time that happens twice** (1:30 AM on the fall-back day): the first one, daylight time, is used.
- **Dates without a time** keep their current meaning in the saved zone. Each is recorded as UTC, so changing the zone later shifts it like any other time.
  - Install or removal date alone: the start of that day (00:00).
  - Ride date alone: noon.
- **Maintenance entries without a time** stay calendar dates. They count the whole day and are shown as a date only.
- **"Cannot be in the future"** checks compare the recorded instant with the current instant.
- **No zone saved** (UTC): typed times are recorded unchanged, as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every time the rider types (US1 scenario 6) MUST be interpreted in the saved zone, using the offset in force on that date, and recorded as a UTC instant.
- **FR-002**: Every stored time MUST be shown in the saved zone and clock format with the zone abbreviation. Dates without a time are shown as dates.
- **FR-003**: Edit forms MUST prefill local date and time, so opening and saving without changes leaves the recorded instant unchanged. This includes Strava rides.
- **FR-004**: The rules for nonexistent and repeated times MUST be the ones in Edge Cases.
- **FR-005**: The update MUST convert every existing typed time exactly once, using the saved zone and each value's own date. Computed totals (bike and part mileage, period Miles, maintenance mileage-at-service, schedule progress) MUST be unchanged by the conversion.
- **FR-006**: Backups made after this change MUST be marked as a newer format. Restoring an older backup MUST convert its typed times using that backup's saved zone, and is otherwise all-or-nothing as today.
- **FR-007**: Comparisons between rides, install periods, maintenance entries and schedules MUST use UTC instants only. The special rules for telling typed times from recorded ones (015 FR-013, 049, 051) are retired, and results are the same as before for the rider's current data.
- **FR-008**: The Settings time zone card MUST stop saying that typed times are shown as typed. It explains that every time is recorded in UTC and shown in this zone.
- **FR-009**: Specs whose rules this replaces MUST be amended to point here: 023 (display), 015 FR-013 and 051 (comparison clock), 036 (typed times without a zone), 049, 038 and 039 where they describe typed times.

## Key Entities

- **Typed time**: a date with an optional time the rider enters. From now on it is stored as a UTC instant like every other time, except maintenance entries without a time, which stay calendar dates.

## Success Criteria *(mandatory)*

- **SC-001**: In the Rides list, manual and Strava rows show times in the same format, with the zone abbreviation.
- **SC-002**: After the update, every mileage total, period total and schedule progress value matches its value before the update.
- **SC-003**: Opening any Edit form and saving it unchanged never moves a time.
- **SC-004**: Changing the zone shifts every displayed time by the same amount, with no exceptions for typed times.

## Assumptions

- The rider typed existing times in the zone that is saved now (New York). Times typed while the zone was still UTC are converted with the saved zone too, since they were meant as local times.
- Single rider, so no per-entry zone is kept. If the rider travels, times are entered and shown in the one saved zone.
- The date pickers stay the browser's own. Only what is stored and shown changes.
