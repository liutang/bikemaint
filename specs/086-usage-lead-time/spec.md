# Feature Specification: Usage Lead Time

**Feature Branch**: `086-usage-lead-time`
**Created**: 2026-11-18
**Status**: Draft (asked by the rider and settled with a mock-up on 2026-11-18; not yet approved for planning)
**Input**: The rider, 2026-11-18, after a backtest showed due dates can be months off: "queue … the mileage-based warning. However, I don't like percentage of schedule. I'd rather have a flat #, such as 20 miles left." Then: "can you add lead miles and rides to the same card in settings instead? Notify when any are crossed."

Answers, 2026-11-18:
- **Hours are included.**
- **The lead applies only while a part is installed.**
- **An interval shorter than its lead is allowed** ("Let it be due soon").

## Background

Today a schedule becomes due soon, on the attention board and as one notification per cycle, only when its estimated date is within the Lead time (days, in Settings). If the estimate is too late, the warning is too. Madone SLR7 Chain 3 went 74 mi past its 186 mi Lube/Wax with no warning, because the date estimate lagged a summer of heavier riding. What's left in miles is always exact.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set how much left counts as due soon (Priority: P1)

**Independent Test**: In Settings, the Lead time card shows Days 7, Miles 20, Rides 2, Hours 2. Changing Miles to 25 saves at once (the card auto-saves) and reads "Currently 7 days, 25 miles, 2 rides or 2 hours, whichever comes first."

**Acceptance Scenarios**:

1. **Given** Settings, **Then** the Lead time card asks "Notify me when a schedule has this much left" with four numbers: Days (the existing lead time), Miles (default 20), Rides (default 2) and Hours (default 2).
2. **Given** a change, **Then** it auto-saves like the other Settings cards. Each value must be 0 or more (and a whole number for days and rides). A refusal reads "Not saved" with the reason, as other cards do.
3. **Given** the card, **Then** its summary reads "Currently D days, M miles, R rides or H hours, whichever comes first."

---

### User Story 2 - Due soon by what's left (Priority: P1)

**Independent Test**: A chain on a bike with a 186 mi Lube/Wax schedule and 18 mi left, whose estimated date is 30 days away, with a 7-day lead and a 20 mi lead. It's due soon on the attention board, and one due-soon notification is sent.

**Acceptance Scenarios**:

1. **Given** a usage schedule on a part installed on a bike, or on a bike, **Then** it's due soon as soon as either:
   - what's left (in its unit) is at or under the matching lead (Miles, Rides or Hours); or
   - its estimated date is within the Days lead, as today.

   Whichever comes first.
2. **Given** a part in storage, **Then** the Miles, Rides and Hours leads don't apply. It shows what's left but isn't due soon from them until it's back on a bike. Overdue still shows.
3. **Given** a period schedule (years, months, weeks), **Then** only the Days lead applies, as today.
4. **Given** a schedule becomes due soon by either rule, **Then**:
   - the due-soon notification and webhook fire once for that cycle (the existing `(schedule_id, cycle_number)` rule);
   - muting still stops them (045);
   - the schedule's own "Receive notifications" switch still applies.
5. **Given** a schedule whose interval is at or under its lead (for example 15 mi with a 20 mi lead), **Then** it's due soon right after each service. The rider accepted this.

### Edge Cases

- **Due soon by miles with a later date:** the urgent card's ring shows what's left, for example "18 mi", instead of days. Its fill is the share of the lead used, the same way the days ring fills today.
- **A lead of 0** turns that unit's rule off.
- **Overdue** is unchanged: past the interval, or past the date.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The account MUST hold lead miles, lead rides and lead hours (defaults 20, 2, 2), set on the Lead time card with the existing lead days, and included in backups like the other settings.
- **FR-002**: A usage schedule MUST be due soon when what's left is at or under its unit's lead, or when its date is within the days lead, whichever comes first, but the usage leads only while the part is on a bike (or the schedule is a bike's).
- **FR-003**: The attention board's due soon and the due-soon notification MUST use the same rule (one place decides).
- **FR-004**: A lead of 0 MUST turn that unit's rule off.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a replay of SLR7 Chain 3's 2026 cycle with a 20 mi lead, it turns due soon on the ride that brings it to 166 mi, before it's overdue.
- **SC-002**: No part in storage is due soon from a usage lead.

## Assumptions

- **No change to webhook fields;** only when the notification fires changes.
- **One rule:** `schedule_service.due_status` and `notification_service.check_due_schedules` share the decision.
- **Amends:** 001 (due-soon and notification rules), 040, 045 and 061 (notifications), 003's attention-board contract (the ring for usage due soon), and CLAUDE.md.
