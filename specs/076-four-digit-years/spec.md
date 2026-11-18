# Feature Specification: Four-Digit Years, Two-Digit Typing

**Feature Branch**: `076-four-digit-years`
**Created**: 2026-11-18
**Status**: Draft (the rider asked for it on 2026-11-17 and answered the review on 2026-11-18; not yet approved for planning)
**Input**: Two requests from the rider on 2026-11-17:
- "queue the four-digit years fix with the next batch"
- "for the fix, allow me to type in two digits when i enter. for example 7/17/26." Answering what 26 means: "20xx is fine."

Answers from the review on 2026-11-18:
- The bike's model Year also reads a two-digit year as 20yy.
- Ride dates in the future are refused, "since that shouldn't exist" (added 2026-11-18).
- Stored times that already have a short year are repaired at startup and on every backup restore.

## Background

On the live instance, the GRX brake pads showed 0 miles although their install date looked right.

- **The cause:** the install date had been typed long ago as year `0021`, a typo for 2021.
- **What 075 did with it:** 075 converted every typed time to UTC. The production server writes years without leading zeros, so the stored instant became `21-04-18T04:56:02.000000Z`. Stored times are compared as text, and `21-…` sorts after every real date, so the period seemed to start after every ride.
- **What was fixed so far:** the rider fixed that one row by hand. No other malformed value was found.
- **Why it can happen again:** a typed year below 1000 is still stored that way.
- **Why it's easy to do:** the browser's date field takes whatever digits are typed for the year. Typing `7/17/26` sends the year `0026`, not 2026.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A two-digit year means 20yy (Priority: P1)

The rider types a date with a two-digit year, for example 7/17/26. The app reads it as 2026-07-17, stores it with a four-digit year, and shows it as 2026.

**Why this priority**: It is the request. It also stops the most likely way a short year gets in: typing the year the way it is written by hand.

**Independent Test**: With the zone set to New York, add a manual ride dated 7/17/26 at 9:00 AM. It is listed as `2026-07-17 9:00AM EDT`, and the bike's total includes it like any ride that day.

**Acceptance Scenarios**:

1. **Given** a date form, **When** the rider types a year from 0 to 99, **Then** it is read as 2000 to 2099. For example, 26 is 2026 and 0 is 2000.
2. **This applies to every typed date:**
   - manual rides and ride edits;
   - install and removal dates when logging or editing a period, on a part's or a bike's Install History;
   - the install date given when adding a part in the builder;
   - maintenance entries (Log and Edit).
3. **Given** a form saved with a two-digit year, **When** it is shown again (after saving, or refused for another reason such as an overlapping period), **Then** the year reads as the four-digit year, for example 2026.
4. **Given** the bike's model Year on Add or Edit bike, **When** the rider types 23, **Then** it is saved as 2023. The usual range, 1900 to next year, is then checked: 99 means 2099 and is refused with the existing "Year must be between 1900 and …" message.
5. **Given** a two-digit year that lands in the future, **Then**:
   - Install and removal dates are refused with "… cannot be in the future.", as today.
   - Ride dates are refused too (US1 scenario 6).
   - Maintenance dates are accepted, as they are today for any future date.
6. **Given** the Add ride or Edit ride form, **When** the date is after today (in the saved zone), or it is today with a typed time later than now, **Then** the form is refused with "The ride date cannot be in the future." and nothing is saved.
   - This is new: until now any future ride date was accepted.
   - A ride for today with no time is accepted at any hour (it is still stored as noon, 075).
   - Strava rides are never checked.

---

### User Story 2 - Stored years always have four digits (Priority: P1)

Every time the app stores has a four-digit year, so stored times always compare in time order.

**Why this priority**: This is what hid the pads' miles. Text comparisons are correct only when every value has the same shape.

**Independent Test**: Store a time for a year below 1000 (only reachable from code, since typing now refuses it) on a server that writes short years. It is stored as `0999-…`, with four digits.

**Acceptance Scenarios**:

1. **Given** any date and time the app converts to a stored instant, **Then** the year is written with four digits, zero-padded. It does not depend on the server: the live server writes `21` where a Mac writes `0021`.
2. **Given** a typed year from 100 to 1899, **Then** the form refuses it with "Enter a valid date", and nothing is saved. A year from 1900 on is accepted as it is today, so a three-digit typo like 202 is refused rather than saved.

---

### User Story 3 - Short years already stored are repaired (Priority: P2)

Any stored time with a year below 100, whether written as `21-…` or `0021-…`, is rewritten as 20yy, as if it had been typed that way. This happens once when the update first starts, and again on every backup restore.

**Why this priority**: The rider's hand fix covered the live database. Rolling backups taken before it still hold the bad pads date, and restoring one would bring the 0 miles back.

**Independent Test**: Restore a backup whose pads period starts at `21-04-18T04:56:02.000000Z` with the zone set to New York. The period starts at `2021-04-18T04:00:00.000000Z` (midnight EDT on 2021-04-18) and the pads' miles count every ride since then.

**Acceptance Scenarios**:

1. **Given** a stored instant with a year below 100, **Then** it is read back as the local date and time it was typed as (in the saved zone), the year becomes 20yy, and it is stored again as UTC with that year's real offset.
   - For example, `21-04-18T04:56:02.000000Z` in New York was typed as 2021-04-18 00:00. It becomes `2021-04-18T04:00:00.000000Z`.
2. **This covers every value the rider types:**
   - manual rides;
   - install and removal moments;
   - maintenance entries: the instant, the local date and the time;
   - schedule starting points.
   - Strava rides are never touched.
3. **Given** the update starts for the first time, **When** short years are found, **Then** they are repaired in one step, which is recorded as done and never runs again. Totals are recomputed.
4. **Given** a backup restore, **Then** short years in the restored rows are repaired in the same step, before totals are recomputed. This applies to both backup formats.
5. **Given** a database or backup with no short years, **Then** nothing changes.

### Edge Cases

- **A typed year of 0, 00 or 0000:** 2000.
- **A date that exists only in some years:** 2/29/24 is 2024-02-29, a real leap day. A short-year leap day that has no 20yy match can't be typed: the browser refuses an invalid date before sending it.
- **Old typed years that were really 19yy:** there are none in the data. The rider chose 20yy for every short year.
- **A short year in a ride's or entry's date shown before saving:** the browser's date field keeps showing `0026` until the form is saved, because no script may rewrite it (constitution). After saving, it reads 2026.
- **Repairing a date that is invalid as 20yy:** a stored `0023-02-29` (an invalid 2023 date) would fail to repair. It can't occur, since year 23 has no leap day in either calendar. If any value can't be repaired, it is left unchanged and logged as a warning naming its table and id. It is never deleted.
- **A repaired period that now overlaps another of the part's periods:** it is repaired anyway and logged as a warning. The rider can fix it on Install History. Install History already refuses new overlaps; this does not try to resolve existing ones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A typed date whose year is 0 to 99 MUST be read as 2000 + that year, everywhere a date is typed (US1 scenario 2). This happens before every other date check.
- **FR-002**: The bike's model Year MUST read 0 to 99 as 2000 + that year before its range check.
- **FR-003**: A typed year from 100 to 1899 MUST be refused with "Enter a valid date", with nothing saved. This does not apply to the bike's model Year, which keeps its own message.
- **FR-004**: Every stored instant the app writes MUST have a zero-padded four-digit year, on every platform.
- **FR-005**: A form shown again after a save or a refusal MUST show the four-digit year.
- **FR-006**: The first start of this update MUST repair every stored short year in the typed columns (US3 scenario 2), once, in one step recorded as done. Totals are recomputed afterwards.
- **FR-007**: Restoring a backup MUST apply the same repair to the restored rows, before totals are recomputed.
- **FR-008**: A repair MUST keep the local date and time the rider typed, change only the year to 20yy, and re-convert with that date's real offset in the saved zone.
- **FR-009**: Strava rides MUST NOT be changed.
- **FR-010**: A value that can't be repaired MUST be left unchanged and logged as a warning with its table and id.
- **FR-011**: Adding or editing a ride MUST refuse a date after today, or today with a typed time later than now, with "The ride date cannot be in the future.", with nothing saved. Rides already stored with a future date are left as they are, and editing one is refused until its date is corrected.

### Key Entities

- **Stored instant**: UTC text `YYYY-MM-DDTHH:MM:SS.ffffffZ` (075). This feature guarantees that `YYYY` is always four digits.
- **Typed date**: what a date field sends, `YYYY-MM-DD`. The browser zero-pads a short year, so `0026` means 26.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Typing 7/17/26 on each form in US1 scenario 2 stores and shows 2026-07-17.
- **SC-002**: No stored instant written by the app has a year shorter than four digits, on the production image's platform.
- **SC-003**: Restoring a backup that holds the old pads value gives the pads the same miles they show today on the live instance.
- **SC-004**: A database with no short years is unchanged by the update: every row and total is identical.

## Assumptions

- **Why 20yy:** the rider chose 20yy for every short year ("20xx is fine"). A 19yy pivot for years that land in the future was not used.
- **Future dates:** maintenance dates may still be in the future; ride dates may not (FR-011). This amends 006 (manual rides).
- **A ride typed for today with no time:** it is accepted at any hour, so a morning entry isn't refused for its default noon time.
- **Which values get repaired:** the same columns 075 converted, plus the maintenance entry's local date, which could hold `0021-…` from before 075.
- **Data steps:** the repair runs as a data step after the SQL migrations, like 075's conversion, recorded in `schema_version`.
  - Unlike 075, it makes no database copy first. It changes only values already broken, and the rider's daily backups exist.
- **Amends 075:** FR-001 (typed times) and the stored-times contract, which gains the four-digit rule.
