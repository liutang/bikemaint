# Feature Specification: Store Typed Times in UTC

**Feature Branch**: `075-typed-times-utc`
**Created**: 2026-11-16
**Status**: Draft, revised 2026-11-16 after review (spec requested by the rider; not approved to build)
**Input**: "Type my time in local time, use timezone setting to record the time as UTC in the DB to match Strava. Then convert back to local time for display purposes." For example, a manual ride typed as 5:39 PM with the zone set to New York (EST) is recorded as 10:39 PM UTC. It is then shown as 5:39 PM EST, the same way Strava rides are shown.

## Background

Today the app keeps two kinds of time:

- **Recorded instants**: Strava rides, completed tasks, "now" install times. These are UTC, shown in the saved zone with its abbreviation, for example `2026-11-13 2:26PM EST`.
- **Typed times**: manual rides, install and removal dates on Install History, and maintenance entry dates and times. These are stored exactly as typed, with no zone, and shown without an abbreviation, for example `2026-11-16 5:00PM`.

Because of this:

- The Rides list mixes labelled and unlabelled times.
- The app needs special rules (015 FR-013, 049, 051) to compare the two kinds. Mileage totals and install periods use those rules.
- Two calculations do not use them, and compare the two kinds directly: a maintenance entry's mileage at service (038) and a schedule's count of miles, rides and hours since its starting point (040). A ride within a few hours of a service time can land on the wrong side of it.
- Editing a Strava ride's time prefills the form with the UTC clock time, not the local one.
- "Today" is the server's date, not the rider's. On a server running on UTC, evenings in New York already count as tomorrow for due dates, and Mark done dates its entry tomorrow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed times are recorded like Strava times (Priority: P1)

The rider types a time in local time. The app records it as a UTC instant using the saved zone, and shows it back in local time with the zone's abbreviation, like every Strava ride.

**Why this priority**: It is the request. One kind of time everywhere means one display rule and one comparison rule.

**Independent Test**: With the zone set to New York, add a manual ride at 2026-11-16 5:39 PM. It is stored as `2026-11-16T22:39` UTC and listed as `2026-11-16 5:39PM EST`, in the same format as the Strava rows.

**Acceptance Scenarios**:

1. **Given** the zone is New York, **When** the rider adds a manual ride on 2026-11-16 at 5:39 PM, **Then** it is recorded as 22:39 UTC and listed as `2026-11-16 5:39PM EST`.
2. **Given** a summer date, **When** the rider types 2026-07-04 at 9:00 AM, **Then** it is recorded as 13:00 UTC (EDT is UTC-4) and listed as `2026-07-04 9:00AM EDT`. Each date uses the offset in force on that date.
3. **Given** a manual ride with no time, **Then** it counts as noon on that date in the saved zone, as today. It is recorded in UTC and listed as `12:00PM`, as today.
4. **Given** any typed time, **When** the rider opens its Edit form, **Then** the date and time fields show the local date and time.
5. **Given** an Edit form, **When** the rider saves it without changing the date and time fields, **Then** the recorded instant stays exactly as it was, seconds included.
6. **Given** a Strava ride, **When** the rider opens its Edit form, **Then** the time field shows its local time (today it shows UTC).
7. **The same rule applies to every place a time is typed:**
   - manual rides and ride edits;
   - install and removal moments on a part's or a bike's Install History (Log and Edit period);
   - the install date given when adding a part;
   - maintenance entries that have a time (Log and Edit maintenance).
8. **Given** a stored time, **Then** it is shown everywhere as `date time ABBR` in the saved zone and clock format. This covers the Rides list, Install History and Maintenance history.

---

### User Story 2 - Maintenance entries keep the date the rider typed (Priority: P1)

A maintenance entry logged at 9:00 PM on November 16 in New York is 02:00 UTC on November 17. It must still be a November 16 entry everywhere the rider sees or relies on its date.

**Why this priority**: Without this rule, evening entries would be listed and counted a day late.

**Independent Test**: With the zone set to New York, log maintenance on 2026-11-16 at 9:00 PM and another on 2026-11-17 with no time. The first reads `2026-11-16 9:00PM EST`, sits below the second in the history, and a schedule by months that starts from it counts from November 16.

**Acceptance Scenarios**:

1. **Given** an entry with a time, **Then** its date and time are those of its recorded instant in the saved zone, never the UTC date.
2. **Given** an entry without a time, **Then** it stays a calendar date and is shown as a date only.
3. **Given** a maintenance history, **Then** it is ordered by the date shown, latest first, then by the time shown. An entry without a time sorts by the local time it was recorded (044, now in one clock).
4. **Given** a schedule by years, months or weeks that starts from an entry, **Then** it counts from the date that entry shows.
5. **Given** a ride, an install period or a schedule's usage count is compared with an entry, **Then** an entry with a time counts at its instant, and an entry without a time counts the whole of that day in the saved zone (038 FR-002).
6. **Given** the rider marks a schedule done, **Then** the entry is dated today in the saved zone (see User Story 5).

---

### User Story 3 - Existing typed times are converted once (Priority: P1)

**What is converted**:

| Stored time | How it is recognised | What happens |
|---|---|---|
| Manual rides | Added by hand | Converted |
| Strava rides, edited or not | From Strava | Left alone (already UTC) |
| Install and removal moments typed by the rider | Whole minutes | Converted |
| Install and removal moments recorded at the moment | Have seconds | Left alone (already UTC) |
| Maintenance entries with a time | Have a time | Recorded as an instant. The date and time shown stay the same |
| Maintenance entries without a time | No time | Left alone (calendar dates) |
| Schedule starting point taken from a typed time | Whole minutes | Converted |
| Schedule starting point taken from an entry without a time | The last moment of a day | Becomes the end of that day in the saved zone |
| Schedule starting point recorded at the moment (created or marked done) | Any other value with seconds | Left alone (already UTC) |
| Schedule starting point "since tracking began" | Its fixed marker | Left alone |
| Record-keeping times (created, updated, synced, completed, notified) | Not typed by the rider | Left alone (already UTC) |

**Acceptance Scenarios**:

1. **Given** existing typed times, **When** the app is updated, **Then** each one in the table is converted once to UTC, using the saved zone and the offset in force on its own date. A manual ride typed as 2026-11-16 5:00 PM becomes 22:00 UTC and still reads `2026-11-16 5:00PM EST`.
2. **Given** the update has run, **Then** these are identical to before:
   - every bike's and part's mileage;
   - every install period's Miles and Rides;
   - every maintenance entry's date, time, order and place in bike and part histories;
   - the mileage saved on every existing maintenance entry.
3. **Given** the update has run, **Then** a schedule's count of miles, rides or hours MAY change, only for rides within a few hours of its starting point. Each change is a correction of the fault described in Background.
4. **Given** the update is about to run, **Then** the app first saves a copy of the whole database beside it, named with the date. If the copy cannot be written, nothing is converted and the app stops with a clear message in its log.
5. **Given** the update fails part-way, **Then** nothing is converted. It runs again at the next start.
6. **Given** the update has run, **Then** it is recorded and never runs again, whatever happens later.
7. **Given** a backup file made before this change, **When** it is restored, **Then** its typed times are converted by the same table, using the zone saved in that backup.

---

### User Story 4 - Changing the zone later (Priority: P2)

**Acceptance Scenarios**:

1. **Given** typed times were recorded in New York, **When** the rider changes the zone to Los Angeles, **Then** every time is shown in Los Angeles time, three hours earlier, with PST or PDT. This includes manual rides, install moments and maintenance times. Strava rides behave this way today.
2. **Given** a zone change, **Then** no ride, install or timed maintenance instant changes, and mileage and period totals stay the same. (An untimed maintenance entry's whole day follows the new zone, since it is a date, not an instant.)
3. **Given** a zone change, **Then** maintenance entries without a time keep their date, and schedules already counting keep their starting point.

---

### User Story 5 - "Today" is the rider's date (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the zone is New York and it is 8:00 PM on November 16 there (01:00 UTC on November 17), **Then** due dates, days remaining, days late and due-soon notifications all treat today as November 16.
2. **Given** the same moment, **When** the rider marks a schedule done, **Then** the maintenance entry and the next cycle are dated November 16.

### Edge Cases

- **A time that doesn't exist** (2:30 AM on the spring-forward day): it is read with the offset in force before the change, so it is recorded as 3:30 AM daylight time and shown that way.
- **A time that happens twice** (1:30 AM on the fall-back day): the first one, daylight time, is used. A Strava ride in the second one keeps its instant when its form is saved unchanged (US1 scenario 5).
- **Dates without a time** keep their current meaning in the saved zone. Each is recorded as UTC, so it is shown with that time and changing the zone later shifts it like any other time.
  - Install or removal date alone: the start of that day (12:00 AM).
  - Ride date alone: noon.
- **Maintenance entries without a time** are the one exception. They stay calendar dates (User Story 2).
- **The repeated hour and totals**: a ride and a typed boundary in the same repeated hour of a fall-back day may now fall on the correct side of each other. This is the one exception to "totals unchanged", and it is not handled further.
- **"Cannot be in the future"** checks compare the recorded instant with the current instant.
- **No zone saved** (UTC): typed times are recorded unchanged, as today. Choosing a zone later then shifts every time already typed, so the zone should be chosen first. This rider has one saved.
- **Strava rides edited before the update**: today the Edit form shows these in UTC, and what is saved is treated as UTC. The update keeps that reading, so they are left alone and totals do not move. The rider has edited none, so no check of them is offered.
- **Entries dated by Mark done in the evening before this change** may carry the next day's date (Background). They cannot be told from correct ones and are left alone. The rider can edit them.
- **Going back to an older version** after the update needs the saved copy from US3 scenario 4 put back. An older version would misread converted times.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every time the rider types (US1 scenario 7) MUST be interpreted in the saved zone, using the offset in force on that date, and recorded as a UTC instant.
- **FR-002**: Every stored instant MUST be shown in the saved zone and clock format with the zone abbreviation. A ride or install date typed without a time is an instant (noon or the start of the day) and is shown with that time. Only a maintenance entry without a time is shown as a date alone.
- **FR-003**: Edit forms MUST prefill the local date and time, including for Strava rides. Saving a form whose date and time fields were not changed MUST leave the recorded instant exactly as it was.
- **FR-004**: The rules for nonexistent and repeated times MUST be the ones in Edge Cases.
- **FR-005**: A maintenance entry's date MUST be its date in the saved zone (US2). History order, date-based schedules and the whole-day rule for entries without a time MUST use that date.
- **FR-006**: The update MUST convert the stored times in the US3 table exactly once, using the saved zone and each value's own date, and MUST leave the others alone.
- **FR-007**: After the update, the figures in US3 scenario 2 MUST be identical to before. Schedule usage counts MAY change only as in US3 scenario 3. Mileage already saved on maintenance entries MUST NOT be recalculated.
- **FR-008**: The update MUST save a copy of the database first, MUST be all-or-nothing, and MUST be recorded so it cannot run twice (US3 scenarios 4 to 6).
- **FR-009**: Backups made after this change MUST be marked as a newer format. Restoring an older backup MUST convert it by the US3 table using that backup's saved zone, and is otherwise all-or-nothing as today.
- **FR-010**: Comparisons between rides, install periods, maintenance entries and schedules MUST use UTC instants only. The special rules for telling typed times from recorded ones (015 FR-013, 049, 051) are retired. Mileage at service (038) and schedule usage counts (040, 043, 046) MUST use the same comparison.
- **FR-011**: "Today" MUST be the current date in the saved zone for due dates, days remaining and late, due-soon notifications and the date Mark done records (US5).
- **FR-012**: Strava rides edited before the update MUST be left as UTC (Edge Cases).
- **FR-013**: The Settings time zone card MUST stop saying that typed times are shown as typed. It explains that every time is recorded in UTC and shown in this zone.
- **FR-014**: Specs whose rules this replaces MUST be amended to point here: 023 (display), 015 FR-013 (comparison clock), 036 (typed times without a zone), 044 (order of entries without a time), 038, 039, 040 and 067, and the 049 and 051 rules recorded in CLAUDE.md (they have no spec folders) where they describe typed times, today's date or the backup format.

## Key Entities

- **Instant**: a moment recorded in UTC. From now on every stored time is one, whether it came from Strava, from the clock or from the rider's typing.
- **Maintenance entry**: has an instant when the rider gave a time. Without a time it is a calendar date. Either way, its date is the rider's local date.
- **Schedule starting point**: the moment a schedule counts from. It is an instant, converted by the US3 table.
- **Pre-update copy**: the copy of the database saved before the one-time conversion.

## Success Criteria *(mandatory)*

- **SC-001**: In the Rides list, manual and Strava rows show times in the same format, with the zone abbreviation.
- **SC-002**: After the update, every bike and part mileage, every period's Miles and Rides, and every maintenance entry's date, time and saved mileage match their values before the update.
- **SC-003**: Opening any Edit form and saving it without touching the date and time never moves a time, by even a second.
- **SC-004**: Changing the zone shifts every displayed time by the same amount. The only things that do not shift are maintenance entries without a time.
- **SC-005**: No maintenance entry is listed, ordered or counted under a date other than the rider's local date.
- **SC-006**: At 8:00 PM local time, nothing in the app treats the date as tomorrow.
- **SC-007**: Starting the updated app a second time changes no stored time.

## Assumptions

- The rider typed existing times in the zone that is saved now (New York). Times typed while the zone was still UTC are converted with the saved zone too, since they were meant as local times.
- Single rider, so no per-entry zone is kept. If the rider travels, times are entered and shown in the one saved zone.
- The date pickers stay the browser's own. Only what is stored and shown changes.
- The rider has not edited any Strava ride, so every Strava ride holds Strava's own UTC time (confirmed by the rider 2026-11-17).
- Schedule usage counts that change (US3 scenario 3) are not reported one by one. The corrected values simply appear (confirmed by the rider 2026-11-17: not worth a report).
