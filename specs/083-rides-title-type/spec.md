# Feature Specification: Ride Titles and Activity Types

**Feature Branch**: `083-rides-title-type`
**Created**: 2026-11-18
**Status**: Draft (asked and settled by the rider on 2026-11-18; not yet approved for planning)
**Input**: The rider, 2026-11-18: "on the rides screen, instead of note, can you download the Title instead? Also, is it possible to pull a thumbnail of the ride and the activity type? So the columns would be: thumbnail, Date&time, title, miles, moving time, activity type, total. I don't need source. If it's a manual input, then the thumbnail can be blank."

The rider's answers, 2026-11-18:
- **No thumbnail:** dropped as "not worth the effort".
- **Strava rides' title and type are read-only.**
- **A note typed on a Strava ride shows under its title.**
- **Manual rides are simple:** the Note field becomes Title, pre-filled "Manual Ride"; their activity type shows "Manual"; there's no type picker; and they always count, as today ("Yes, show Manual").
- **The Actions column stays** (confirmed).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rides are listed by title and type (Priority: P1)

**Why this priority**: It is the request. Rides are easier to recognise by name than by a note column that is mostly empty.

**Independent Test**: A bike with a synced "Morning Ride" (Strava type Ride), a synced "Gravel loop" (GravelRide) and a manual ride whose note was "Trainer". Its Rides list shows:
- the columns Date & time, Title, Miles, Moving time, Activity type, Total, Actions;
- the titles "Morning Ride", "Gravel loop" and "Trainer";
- the types "Ride", "Gravel ride" and "Manual".

**Acceptance Scenarios**:

1. **Given** any Rides list (a bike's, a part's, or an install period's), **Then** its columns are Date & time, Title, Miles, Moving time, Activity type, Total. A bike's list also has Actions. There are no Source or Note columns.
2. **Given** a Strava ride, **Then**:
   - **Title** is its Strava activity name.
   - **Activity type** is its Strava sport type, as a readable label from the sync-rules list (Ride, Gravel ride, Mountain bike ride, …). A type not in that list is made readable from Strava's name, so `TrailRun` reads "Trail run".
3. **Given** a Strava ride with a note you typed, **Then** the note shows in small text under its title.
4. **Given** a manual ride, **Then** its title is its title (formerly its note), and its activity type reads "Manual".
5. **Given** a Strava ride with no stored title or type yet (synced before 060 and not re-imported since), **Then** those cells are blank.

---

### User Story 2 - Adding and editing a ride (Priority: P1)

**Why this priority**: Manual rides need a title, and Strava rides must not lose their link to Strava by being retitled here.

**Independent Test**:
- **Add a ride:** the form shows a Title field pre-filled "Manual Ride". Saving it with "Trainer" lists the ride as "Trainer", type "Manual".
- **Edit a Strava ride:** its title and type show as text, not fields, and its Note field is still there.

**Acceptance Scenarios**:

1. **Given** the Add ride form, **Then** it has a Title field, pre-filled "Manual Ride", instead of Note. A blank title is saved as "Manual Ride".
2. **Given** the Edit form of a manual ride, **Then** its Title field shows its title. Existing notes on manual rides become their titles.
3. **Given** the Edit form of a Strava ride, **Then**:
   - its title and activity type are shown as text, with the hint "From Strava. Rename it there, then Re-import.";
   - its Note field stays, and saving the form still marks the ride edited, as today.
4. **Given** Re-import of a paired bike, **Then**:
   - its unedited Strava rides get Strava's current title and type, as today;
   - an edited Strava ride with no stored title or type gets them filled in, and nothing else about it changes.

### Edge Cases

- **Long titles** wrap within the Title column. The list doesn't scroll sideways.
- **Phone layout:** the narrow layout keeps its label-per-cell style, with labels "Title" and "Activity type".
- **Sync rules are unchanged:** manual rides always count (060). Keywords still match Strava titles only.
- **A manual ride's title** can be at most 200 characters, the same limit as the note today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every Rides list MUST show Date & time, Title, Miles, Moving time, Activity type, Total, and Actions where it has them today, and no Source or Note columns.
- **FR-002**: A Strava ride's title and activity type MUST come from Strava and MUST NOT be editable in the app.
- **FR-003**: A Strava ride's note MUST show under its title, and MUST stay editable.
- **FR-004**: A manual ride MUST have a title, pre-filled "Manual Ride" on Add, with blank saved as "Manual Ride". Its activity type MUST read "Manual". Existing notes on manual rides MUST become their titles.
- **FR-005**: Re-import MUST fill a missing title or type on an edited Strava ride without changing anything else about it.
- **FR-006**: Manual rides MUST keep counting regardless of sync rules (060, unchanged).

### Key Entities

- **Ride**: `ride_activity`.
  - `activity_name`: the Strava title, or the manual title.
  - `sport_type`: Strava's type, empty for manual rides.
  - `note`: the rider's note, kept for Strava rides.

  Where a manual ride's title is stored is a plan decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every row shows a title or is blank only for an un-reimported old Strava ride, and every manual ride reads "Manual".
- **SC-002**: No Strava ride's title or type can be changed from the app.
- **SC-003**: No existing note is lost. Manual notes become titles, and Strava notes stay under their titles.

## Assumptions

- **Readable labels** reuse `app/models/sync_rules.py` `SPORTS`.
- **The rider re-imports each paired bike** to fill older rides. There's no automatic re-fetch.
- **Amends:** 006 (ride log and form), 039 (Rides columns), 053 (period Rides) and 060 (where the title and type are stored, read-only).
