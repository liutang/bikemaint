# Feature Specification: Strava Sync Settings and Time Zone

**Feature Branch**: `023-settings-sync-and-timezone`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User testing feedback (2026-11-12), items 4 and 6. (4) Add a Strava sync interval in Settings → Strava Connection: turn the sync on or off and set an interval in hours and minutes. (6) Add the ability to set a time zone in Settings; times currently default to UTC. Decided with the rider: the time zone is **display only** (see Assumptions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Control the Automatic Strava Sync (Priority: P1)

As the rider, I want to turn automatic Strava syncing on or off and choose how often it runs, in hours and minutes, so the app fetches my rides as often as I want and not more.

**Why this priority**: The interval is fixed today (set only by a server setting). Rider control over it is the first request.

**Independent Test**: In Settings → Strava connection, set 1 hour 30 minutes and save; the settings page then shows "Every 1 h 30 min". Turn sync off and save; no automatic sync runs, but the manual sync still works.

**Acceptance Scenarios**:

1. **Given** the Strava connection panel, **When** it is shown, **Then** it has an "Sync automatically" switch and Hours and Minutes fields showing the current setting, with a Save button.
2. **Given** a valid interval (for example 2 hours 15 minutes), **When** the rider saves, **Then** the setting is stored, shown back on the page, and the next automatic syncs run at that interval starting from now, without restarting the app.
3. **Given** automatic sync is turned off and saved, **When** time passes, **Then** no automatic sync runs, and the page says automatic sync is off.
4. **Given** automatic sync is off, **When** the rider uses the manual "Sync" action, **Then** the sync runs as before.
5. **Given** automatic sync is turned on again and saved, **When** time passes, **Then** syncs resume at the saved interval.
6. **Given** an interval shorter than 5 minutes, longer than 7 days, or not a whole number, **When** the rider saves, **Then** the page is shown again with a clear message beside the field and nothing changes.
7. **Given** the rider has never saved a value, **When** the app runs, **Then** it uses the server's existing default interval (30 minutes unless the server's setting says otherwise).
8. **Given** the rider saved a value, **When** the app is restarted, **Then** the saved on/off state and interval are used.
9. **Given** the settings routes, **When** requested without signing in, **Then** sign-in is required.

---

### User Story 2 - Show Times in My Time Zone (Priority: P2)

As the rider, I want to choose my time zone, so times the app records in UTC (Strava rides, completed tasks, when Strava was connected) are shown in my local time instead.

**Why this priority**: A correctness-of-reading problem rather than a blocker; builds on the same Settings page.

**Independent Test**: Choose "America/Los_Angeles"; a Strava ride that began at 18:00 UTC shows as 10:00 PST (or 11:00 PDT in summer) on the ride log, with the zone shown.

**Acceptance Scenarios**:

1. **Given** Settings, **When** it is shown, **Then** a "Time zone" section shows the current zone (UTC until the rider chooses one) and a short dropdown of UTC offsets with their usual abbreviations (for example `-05:00 EST`, `-08:00 PST`, `+05:30 IST`), ordered from earliest to latest offset, with a Save button. The list is not a list of countries and cities. *(Changed after user testing, 2026-11-12: it first offered every IANA name.)*
2. **Given** an unknown or empty zone, **When** the rider saves, **Then** a clear message appears beside the field and nothing changes.
2a. **Given** a choice such as `-05:00 EST`, **When** it is saved and times are shown, **Then** daylight saving is applied automatically for that region (EST becomes EDT in summer), and a choice marked "no daylight saving" never changes.
2b. **Given** a zone saved earlier that is not in the short list, **When** Settings is shown, **Then** it appears as the selected current choice so nothing is lost, and saving the form without changing it keeps it.
3. **Given** a chosen zone, **When** the ride log shows a Strava ride, **Then** its date and time are shown in that zone with the zone abbreviation (for example "2026-11-12 10:00 PST"), taking daylight saving into account for that date.
4. **Given** a chosen zone, **When** the maintenance history shows a completed task, **Then** its time is shown in that zone with the abbreviation.
5. **Given** a chosen zone, **When** Settings shows when Strava was connected, **Then** that moment is shown in the zone.
6. **Given** a time the rider typed (a manual ride, a service, an install or removal moment), **When** it is shown, **Then** it is shown exactly as typed; it is not shifted.
7. **Given** the rider types an install or removal moment, **When** it is later than the current time **in the chosen zone**, **Then** it is refused as in the future; a moment that has already passed in that zone is accepted.
8. **Given** a part installed with a blank date ("now"), **When** its mileage is calculated, **Then** the result is the same as before this feature (the moment is still recorded in UTC).
9. **Given** the time zone setting, **When** pages show times, **Then** the previous conversion to the viewing browser's own zone no longer applies; the saved zone is used on every device.
10. **Given** the app running from its container image, **When** any zone is chosen, **Then** it works (the image carries the zone data).

---

### Edge Cases

- Interval boundaries: exactly 5 minutes and exactly 7 days (168 hours, 0 minutes) are accepted; 0 hours 0 minutes and 0 hours 4 minutes are refused.
- Hours and minutes together form one interval: 1 hour 90 minutes is refused (minutes are 0–59); the rider enters 2 hours 30 minutes instead.
- Saving settings while a sync is running does not interrupt it; the new interval applies from the next scheduling.
- Turning sync off then on again must not start two syncs or leave the old schedule running.
- Times with daylight saving: a ride in July and one in January in the same zone show different offsets and abbreviations.
- Existing data is unchanged; only presentation moves.
- Stored times that came from the rider's typing (and "now" defaults recorded in UTC for install periods) keep their stored values; install and removal moments created with a blank date therefore keep showing as recorded (UTC) in Install History. This is a deliberate trade-off to keep mileage exact.
- The edit form for a ride shows the stored value, not a converted one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Settings → Strava connection MUST offer a switch for automatic sync and Hours and Minutes fields for the interval, showing the current values.
- **FR-002**: The interval MUST be at least 5 minutes and at most 7 days, in whole minutes; minutes MUST be 0–59. Invalid input MUST re-show the page with a message beside the field and change nothing.
- **FR-003**: Saving MUST apply immediately (no restart): when on, automatic syncs run at the new interval from that moment; when off, no automatic sync runs.
- **FR-004**: The manual sync action MUST work regardless of the automatic setting.
- **FR-005**: The saved on/off state and interval MUST survive restarts. Until the rider saves a value, the server's existing interval setting (default 30 minutes) MUST apply and automatic sync MUST be on.
- **FR-006**: Settings → Time zone MUST offer a short dropdown of UTC offsets with their usual abbreviations, ordered by offset, each standing for a real region that follows its own daylight saving rules (plus a "no daylight saving" choice where a common region differs, such as Arizona), MUST keep a previously saved zone selectable, and MUST refuse unknown zones with a message beside the field. *(Changed after user testing, 2026-11-12.)*
- **FR-007**: Times the app records in UTC (Strava rides, completed-task times and other system-made timestamps, Strava connected-since) MUST be shown in the chosen zone with the zone abbreviation, accounting for daylight saving on that date.
- **FR-008**: Times the rider typed MUST be shown as typed.
- **FR-009**: The "not in the future" check for typed install and removal moments MUST compare against the current time in the chosen zone.
- **FR-010**: No stored time MUST change, and a blank install date ("now") MUST still be recorded in UTC, so mileage results are unchanged.
- **FR-011**: The conversion to the viewing browser's own zone MUST be removed; the saved zone MUST be used everywhere.
- **FR-012**: The application image MUST include the data needed to resolve every IANA zone.
- **FR-013**: The settings changes MUST require sign-in like every other route and MUST log a readable line when sync scheduling changes (enabled or disabled, interval), without secrets.

### Key Entities

- **Account settings**: the rider's single account gains three settings: automatic sync on/off, sync interval in minutes (unset until saved), and time zone name (UTC until saved).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After saving a new interval, the next automatic sync starts within one interval of the new value, with no app restart (verified by the schedule reporting the new interval).
- **SC-002**: With automatic sync off, 0 automatic syncs run, while the manual sync succeeds.
- **SC-003**: For a chosen zone, 100% of UTC-recorded times on the ride log, maintenance history and Settings are shown in that zone with its abbreviation.
- **SC-004**: Part mileage totals are identical before and after this feature for the same data (suite passes unchanged).
- **SC-005**: A rider can change both settings in under a minute from the Settings page.

## Assumptions

- The time zone is display only (decided with the rider): converting stored times would risk wrong mileage, because rides from Strava and "now" defaults are stored in UTC while typed times are stored as typed.
- The first-run default interval comes from the server's existing `STRAVA_SYNC_INTERVAL_MINUTES` setting (30 minutes if unset); once the rider saves, the saved value wins.
- The rider picks by UTC offset and abbreviation; each choice is backed by one representative standard zone name (for example `-05:00 EST` is `America/New_York`) so daylight saving is correct. Rarely used zones are not listed; a rider who needs one can still have it saved (it then shows as the current choice).
- A zone abbreviation is shown after each converted time (for example PST); where a zone has no letter abbreviation, its UTC offset is shown instead (for example +03).
- The notification check interval is not part of this feature.
- Single rider; settings live on the one account.

## Amendments
- **2026-11-12 (branch `025-timezone-picker`)**: user testing found the time zone dropdown, which listed every IANA city name, unusable. Replaced by a short list of UTC offsets with abbreviations (US2 scenarios 1, 2a, 2b; FR-006; the zone-name assumption).
