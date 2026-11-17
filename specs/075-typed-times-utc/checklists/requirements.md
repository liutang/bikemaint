# Specification Quality Checklist: Store Typed Times in UTC

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-16
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Defaults were chosen without asking, and the rider can override them:
  - Nonexistent and repeated daylight-saving times (Edge Cases).
  - Maintenance entries without a time stay dates.
  - Every time shows its zone abbreviation, including Install History and Maintenance history.
  - Existing data is converted with the zone saved now.
- UTC is named because the rider asked for it by name. It is the stored meaning, not a technology choice.
- The spec is written but not approved to build. Planning waits for the rider.

### Revision 2026-11-16 (review after the first draft)

The first draft was checked against the code and revised. What changed, and why:

- **Totals promise narrowed** (FR-007, SC-002). Mileage at service and schedule usage counts compare Strava's UTC times with typed local times directly today, so they cannot stay identical once the comparison is correct. Bike, part and period totals still must.
- **Maintenance dates** (US2, FR-005). A timed entry's UTC date can be the next day. The entry's date is now defined as its local date for display, order and date-based schedules.
- **Schedule starting points** are named in the conversion table, with how each form is recognised.
- **Edited Strava rides** stay UTC (FR-012).
- **The conversion is one-way**: database copy first, all-or-nothing, recorded so it cannot repeat (FR-008).
- **Date-only rides and installs** are instants and show a time. Only untimed maintenance entries are dates (FR-002).
- **Unchanged save keeps the instant** (FR-003, SC-003), which also covers Strava seconds and the repeated hour.
- **"Today" in the saved zone** was added (US5, FR-011). Mark done dates its entry with the server's date today.

### Rider decisions 2026-11-17

- No report of schedule counts that change: "it's not worth chasing these extreme edge cases."
- No one-time list of edited Strava rides: the rider has edited none, so every Strava ride holds Strava's UTC time. This removes the only new screen content, so the feature needs no mock-up.
- The rider has never used Mark done, so no existing entry carries a server-dated next day.

### Notes for planning (not requirements)

- The conversion needs zone data, so it cannot be a plain `.sql` migration. It needs its own run-once marker.
- The "whole minutes" and "last moment of a day" tests in the conversion table are how the stored text tells the forms apart today. The plan should test each form.
- Once comparisons are UTC-only, the stored text of converted times should be written in one format so plain comparisons are safe.
- The backup format number goes from 1 to 2.
- Whether an untimed entry's "whole day" is stored or worked out when read is a plan decision. Either way US4 scenario 3 must hold.
