# Feature Specification: Blended Riding Pace

**Feature Branch**: `085-blended-pace`
**Created**: 2026-11-18
**Status**: Draft (the rider chose this approach on 2026-11-18 after a backtest; not yet approved for planning)
**Input**: The rider asked how to get "the most reasonably accurate estimate based on the changing rate at which I'm riding my bike". After a backtest on their own data they said: "I'll go with your recommendation. queue the blended approach…".

Answers, 2026-11-18:
- **Low confidence** means too little history.
- **Hours** pace starts at the first recorded moving time.

## Background

A usage schedule (miles, rides, hours) estimates its due date from its bike's pace over the last 90 days. A backtest on the rider's live data, 21 forecasts over 13 completed chain cycles, found:

| Method | Typical miss, all forecasts | Typical miss, steady riding |
|---|---|---|
| The current 90-day window | 22–27 days | 11–12 days |
| The average of the 90-day and whole-history paces | 18 days | 5 days |

- **Where the 90-day window fails:** worst at the start of a cycle (a typical miss of 81 days), when the last 90 days were often quiet, for example after winter.
- **Other methods:** none did better across both steady and changing riding.
- **Bike changes:** when a bike's riding fell sharply mid-cycle, every method was months off.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Due dates use the blended pace (Priority: P1)

**Why this priority**: It is the request, and it gives the smallest typical miss on the rider's history.

**Independent Test**: A bike with 28.7 mi in the last 90 days and 1,353.5 mi over 2,040 days since its first ride gives a pace of (0.319 + 0.663) ÷ 2 ≈ 0.491 mi a day. A chain schedule with 23.3 mi left is due in 48 days.

**Acceptance Scenarios**:

1. **Given** a usage schedule on a bike or a part on a bike, **Then** its pace is the average of two paces:
   - the bike's pace over the last 90 days;
   - the bike's whole-history pace: everything since its first ride, divided by the days since then.

   Its estimated date is today plus what's left divided by that pace.
2. **This applies to every usage unit:**
   - **Miles:** ride miles.
   - **Rides:** ride counts.
   - **Hours:** moving time. Its whole history starts at the bike's first ride with a recorded moving time.
3. **Given** a bike with no rides in the last 90 days, **Then** the pace is half its whole-history pace, so there's still a date.
4. **Given** a part in storage (no bike), **Then** there's no estimated date, as today. What's left is still shown.

---

### User Story 2 - "Low confidence" means too little history (Priority: P2)

**Why this priority**: The old rule ("fewer than 5 ride days in the last 90") flagged every winter. The blend uses the whole history, so the label should say when there isn't enough of it.

**Independent Test**: A bike with 3 rides in total, or whose first ride was 20 days ago, shows "Low confidence". The rider's bikes, with years of rides, don't.

**Acceptance Scenarios**:

1. **Given** a usage schedule whose bike has fewer than 5 rides in total, or less than 30 days since its first ride, **Then** it's marked "Low confidence".
2. **Given** any other bike, **Then** it isn't, whatever the last 90 days held.
3. **Given** a schedule with both a usage and a time side, **Then** the earlier of the two dates is used, as today. A low-confidence usage date still falls back to the time side, as today.

### Edge Cases

- **A bike with no rides at all:** there's no pace, so there's no usage date. It's marked "Low confidence", as today.
- **Filtered-out and deleted rides** don't count toward either pace (same rides as today).
- **Archived bikes** have no active schedules (079), so nothing changes there.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The usage pace MUST be the mean of the bike's 90-day pace and its whole-history pace, for miles, rides and hours.
- **FR-002**: The whole-history pace MUST run from the bike's first ride for miles and rides, and from its first ride with a recorded moving time for hours, to today.
- **FR-003**: "Low confidence" MUST mean the bike has fewer than 5 rides in total, or less than 30 days since its first ride.
- **FR-004**: Everything else about projections (what's left, overdue, the time side, earliest-of-the-two) MUST stay as it is.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the US1 example, the estimated date is 48 days out.
- **SC-002**: None of the rider's current bikes shows "Low confidence" for a usage schedule.

## Assumptions

- **Computed on read, never stored,** like today's projection (001 research §4).
- **"Today" is the saved zone's today** (075).
- **Due-soon notifications** follow the new dates. The flat usage lead (086) is a separate change.
- **Amends:** 001 research §4 (the projection algorithm and low-confidence fallback), 040 (usage projections) and 054.
