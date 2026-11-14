# Feature Specification: 12-Hour Clock Setting

**Feature Branch**: `036-twelve-hour-clock`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14: add a setting to show times on a 12-hour or 24-hour clock, default 12-hour, and show all times in 12-hour by default. Example: a ride now shown as `2026-11-13 14:26 EST` should read `2026-11-13 2:26PM EST`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Times Read on a 12-Hour Clock by Default (Priority: P1)

Every date-and-time the app shows (rides, install history, completed tasks, connection time) uses a 12-hour clock with AM/PM, unless the rider chooses 24-hour.

**Why this priority**: The rider reads times daily and prefers 12-hour.

**Independent Test**: With default settings, open Rides and Install History and confirm times such as `2:26PM`.

**Acceptance Scenarios**:

1. **Given** the default setting, **When** a Strava ride at 14:26 in the saved zone is shown, **Then** it reads `2026-11-13 2:26PM EST`.
2. **Given** the default setting, **When** a typed ride or install time of 07:30 is shown, **Then** it reads `2026-09-02 7:30AM` (no zone, as typed).
3. **Given** noon and midnight, **When** shown, **Then** they read `12:00PM` and `12:00AM`.
4. **Given** a new account, **When** it is created, **Then** the clock is 12-hour.

---

### User Story 2 - Choose 12 or 24 Hours in Settings (Priority: P1)

A "Clock" setting on the Settings screen offers "12-hour" and "24-hour". Saving applies to all screens at once.

**Independent Test**: Switch to 24-hour, reload Rides, and see `14:26`; switch back.

**Acceptance Scenarios**:

1. **Given** Settings, **When** it opens, **Then** the current clock is shown and selectable between 12-hour and 24-hour.
2. **Given** 24-hour is saved, **When** times are shown, **Then** they read `2026-11-13 14:26 EST` and `2026-09-02 07:30` as before this feature.
3. **Given** an invalid value is posted, **When** it is saved, **Then** it is rejected and nothing changes.

### Edge Cases

- Time pickers in forms use the browser's own control and are not changed.
- Existing accounts take 12-hour after upgrade (the new default).
- Dates keep the `YYYY-MM-DD` form.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The account MUST hold a clock setting, `12` or `24`, defaulting to `12` (existing accounts too).
- **FR-002**: UTC-recorded times shown by the app MUST use `YYYY-MM-DD h:MMAM/PM ZONE` on a 12-hour clock and `YYYY-MM-DD HH:MM ZONE` on a 24-hour clock.
- **FR-003**: Typed times shown as typed (rides, install history rows) MUST follow the same setting without a zone label: `YYYY-MM-DD h:MMAM/PM` or `YYYY-MM-DD HH:MM`.
- **FR-004**: Settings MUST offer the choice, validate it server-side, and apply it immediately to every screen.

### Key Entities

- **Account**: gains the clock setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the default setting, no displayed time on Rides, Install History, Maintenance history or Settings is in 24-hour form.
- **SC-002**: Switching the setting changes every displayed time on the next page load.

## Assumptions

- The space between the time and AM/PM is omitted, as in the rider's example (`2:26PM`).
- Display only; stored values do not change.
- **FR-006** *(added by branch `052-local-maintenance-times`)*: A maintenance entry's typed date and time MUST be shown through the same rule as FR-003 (`2026-05-01 2:30PM`) on bike and part histories; an entry with no time shows only the date. Completed-task entries already use FR-002.
