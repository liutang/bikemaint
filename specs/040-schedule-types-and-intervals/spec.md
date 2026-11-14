# Feature Specification: Schedule Service Types and Intervals

**Feature Branch**: `040-schedule-types-and-intervals`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback 2026-11-14 (shown in full under Source). Clarified with the rider: Hours use ride moving time (feature 039); old schedules are not converted automatically, the rider picks per schedule; a schedule has one interval only.

> **Source (rider's words, condensed)**: Service Type (formerly Name) is a drop-down of Charge, Check, Clean, Lube/Wax, Replace, Service, Topup. A schedule has a selector to define the interval by Usage or by Period. A value field takes a number and a drop-down selects units: Usage gives Miles, Rides, Hours; Period gives Years, Months, Weeks. A Recurring selector is on by default: marking the item done generates the next item at the interval; off means no new item. A Receive notifications selector: if enabled, the system sends a webhook notification when one is configured.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Schedule From a Service Type and One Interval (Priority: P1)

On a new schedule form the rider picks a Service Type, chooses Usage or Period, enters a number and picks a unit that fits the choice.

**Independent Test**: Create "Replace, every 2000 miles" and "Check, every 3 months"; both appear on Maintenance due with the right next-due.

**Acceptance Scenarios**:

1. **Given** the new schedule form, **When** it opens, **Then** it has a Service Type drop-down listing exactly Charge, Check, Clean, Lube/Wax, Replace, Service, Topup (no free-text name), an "Interval by" choice of Usage or Period (Usage selected), a number field, a units drop-down, a Recurring switch (on) and a Receive notifications switch (on).
2. **Given** Usage is selected, **When** the units are shown, **Then** they are Miles, Rides, Hours; **given** Period is selected, **Then** they are Years, Months, Weeks. Only the units for the chosen kind are offered and the server rejects any other pairing.
3. **Given** a Service Type, a number above zero and a matching unit, **When** saved, **Then** the schedule is created with the service type as its name and one interval, counting from the last time that service type was logged on that bike or part (see FR-011); only when it was never logged does it count from when tracking began.
4. **Given** a missing Service Type, a number that is blank, zero or negative, or a unit that does not match the kind, **When** saved, **Then** the form re-opens with a message beside the field and nothing is saved.
5. **Given** a schedule by Period, **When** the next due date is worked out, **Then** it is the baseline date plus that many years, months (calendar months; a day past the end of a short month becomes the last day) or weeks.
6. **Given** a schedule by Usage in Miles, Rides or Hours, **When** the next due date is projected, **Then** the remaining usage is the interval minus the usage since the baseline, and the date follows the rider's trailing 90-day pace in that unit, exactly as miles did before; when the usage is already used up the schedule is overdue.

---

### User Story 2 - Recurring or One-Time (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recurring schedule, **When** it is marked done, **Then** maintenance is logged and the next cycle starts from now (as today).
2. **Given** a schedule with Recurring off, **When** it is marked done, **Then** maintenance is logged and the schedule ends: it no longer appears among due items and no further reminders are sent (its history stays).
3. **Given** Edit, **When** the switch is changed, **Then** it applies from the next completion.

---

### User Story 3 - Choose Whether a Schedule Sends Notifications (Priority: P2)

**Acceptance Scenarios**:

1. **Given** Receive notifications on, **When** the schedule is due soon, **Then** the in-app notification is recorded and the webhook is sent if one is configured, as today.
2. **Given** Receive notifications off, **When** the schedule is due soon, **Then** no notification is recorded and no webhook is sent for it; it still shows on Maintenance due.

---

### User Story 4 - Existing Schedules Keep Working Until the Rider Updates Them (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a schedule created before this feature (free-text name, mileage and/or day interval), **When** the app runs, **Then** it keeps its name, projection and notifications unchanged.
2. **Given** such a schedule is opened for Edit, **When** the form opens, **Then** Service Type is empty and required, the interval is prefilled (miles as Usage/Miles; days as Period/Weeks, days divided by 7 and rounded, at least 1), and a note explains that the rider picks a Service Type and checks the interval.
3. **Given** the rider saves it, **When** valid, **Then** it becomes a new-style schedule (the old name is replaced by the Service Type) and keeps its place in the current cycle (baseline unchanged).
4. **Given** an old schedule with both a mileage and a day interval, **When** edited, **Then** the form prefills the mileage interval and the rider chooses.

### Edge Cases

- A schedule by Hours or Rides on a part counts only rides during the part's installation periods (as mileage does).
- A part in storage has no pace, so the date falls back to the Period side, or "no estimate" for usage-only schedules, as today.
- Hours of rides with no recorded moving time count as zero.
- Maintenance entries logged from completion are described by the service type.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A schedule MUST have a service type from the fixed list; new schedules MUST NOT accept free text.
- **FR-002**: A schedule MUST have exactly one interval: a kind (Usage or Period), a positive number, and a unit valid for the kind (Usage: miles, rides, hours; Period: years, months, weeks). Invalid combinations MUST be rejected at the boundary.
- **FR-003**: Period schedules MUST be due at baseline date plus the interval in calendar units.
- **FR-004**: Usage schedules MUST measure usage since the baseline moment: miles (mileage since baseline), rides (count of live rides), hours (sum of moving time); parts count only rides while installed. Pace and confidence rules are those already used for miles.
- **FR-005**: Each schedule MUST have a Recurring flag (default on) and a Receive notifications flag (default on).
- **FR-006**: Completing a schedule MUST log maintenance; if recurring it MUST start the next cycle; if not it MUST end the schedule.
- **FR-007**: Due-soon notification and webhook MUST be skipped for schedules whose Receive notifications flag is off.
- **FR-008**: Old schedules MUST keep working unchanged and MUST be convertible only by the rider through Edit, with the prefill described in User Story 4.
- **FR-009**: The units drop-down MUST offer only the units of the selected kind without any script (constitution: no JS beyond the builder asset).
- **FR-010**: Maintenance due, notifications and webhook text MUST describe remaining usage in the schedule's own unit (miles, rides or hours).

- **FR-011**: A new schedule MUST count from the most recent maintenance entry of the same service type on the same bike or part: its date and time start a Period, and the mileage recorded on it, and the rides and hours after it, start Usage. If none was ever logged, it MUST count from when tracking began: Usage from all rides on the bike or part (excluding its starting mileage; adjustments count), a Period from the part's earliest install date, else when the bike or part was added. A schedule already past its interval on that basis is overdue when created. *(Added by feature 043 after user testing: a Topup logged on a wheel in 2023, then a 4-month Topup schedule, showed "on track" instead of overdue.)*

### Key Entities

- **Schedule**: gains service type, interval kind/value/unit, recurring flag, notify flag, and a baseline moment (used to count rides and hours since the last completion).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can create each of the six unit types in one form submission.
- **SC-002**: Marking a non-recurring schedule done removes it from Maintenance due 100% of the time.
- **SC-003**: A schedule with notifications off never produces a notification or webhook.
- **SC-004**: Schedules created before this feature show the same next-due dates before and after the upgrade.

## Assumptions

- Webhook payload keeps its shape; the projected remaining value is also sent as `projected_remaining` with `projected_remaining_unit`, and `projected_remaining_miles` is kept for miles.
- A baseline moment is recorded at creation and at each completion.
- Ride times are compared as stored (typed times are not zone-converted), as for installation periods.

## Amendments
- **2026-11-14 (branch `043-schedule-backdated-baseline`)**: User Story 1 scenario 3 said a new schedule counts from now. Replaced by FR-011: it counts from the last matching logged service, else from when tracking began. Chosen by the rider.
- **2026-11-15 (branch `046-schedules-follow-maintenance`)**: FR-011 only set the starting point when a schedule was created; logging a newer matching service afterwards left the schedule stale. See `specs/046-schedules-follow-maintenance/spec.md`: logging or editing maintenance restarts matching schedules.

