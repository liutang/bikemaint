# Feature Specification: Quiet Top Bar

**Feature Branch**: `084-quiet-top-bar`
**Created**: 2026-11-18
**Status**: Draft (asked by the rider and settled with mock-ups on 2026-11-18; not yet approved for planning)
**Input**: Three requests from the rider on 2026-11-18, combined into one change at their request ("can #3 and #6 be part of the same change?"):
- "change the banner text for 'Maintenance due' to 'Maintenance'";
- "For the strava connection sync status, I only need the bubble on the top header bar. If I want to know when the last sync was (e.g. synced 7 mins ago), I can go into settings and it should show in the Strava connection card." Later: "include time in hover text as well";
- "remove the Sign out text from the sign out button. You can add hover text to show Sign out."

The rider also confirmed the Mute card's new wording.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A shorter Maintenance link (Priority: P1)

**Independent Test**: The top bar's wrench link reads "Maintenance" and opens the same page, whose heading is still "What needs attention".

**Acceptance Scenarios**:

1. **Given** any signed-in page, **Then** the top bar link to `/maintenance/due` reads "Maintenance".
2. **Given** Settings, **Then** the Mute card reads "Schedules still appear under Maintenance." instead of "… on Maintenance due."

---

### User Story 2 - The sync dot on its own (Priority: P1)

**Independent Test**: The top bar shows the coloured dot with no text. Hovering it reads "Sync is working · 7 min ago". The Strava connection card in Settings shows "Sync is working. Last synced 7 minutes ago (2026-11-18 6:12PM EST)." with the same dot.

**Acceptance Scenarios**:

1. **Given** any signed-in page, **Then** the top bar shows only the sync dot, with its colour as today (FR-006b). Its hover text and accessible name give the state and how long ago the last sync was, for example "Sync is working · 7 min ago".
2. **Given** the Strava connection card, **Then** below "Connected since…" a line with the matching dot reads:

   | State | Line |
   |---|---|
   | Working | "Sync is working. Last synced 7 minutes ago (2026-11-18 6:12PM EST)." |
   | Not working | "Sync isn't working. Last successful sync 3 hours ago (…)." |
   | Automatic sync off | "Automatic sync is off. Last synced 2 days ago (…)." |
   | Never synced | "Not synced yet." |

3. **Given** a phone-width screen, **Then** the top bar no longer gives the sync status a row of its own.

---

### User Story 3 - An icon-only Sign out (Priority: P2)

**Independent Test**: The Sign out button shows only its icon. Hovering it reads "Sign out", and pressing it signs out at once.

**Acceptance Scenarios**:

1. **Given** the top bar, **Then** Sign out is an icon button like the row actions elsewhere, with the hover text and accessible name "Sign out". It still signs out immediately.

### Edge Cases

- **The relative time** is worked out when the page is shown, as today. A page left open shows the time from when it loaded.
- **Screen readers** read the dot's and the button's names, so no information depends on colour or an icon alone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The top bar's link to Maintenance due MUST read "Maintenance". The Mute card text MUST read "Schedules still appear under Maintenance."
- **FR-002**: The top bar MUST show the sync dot without text. Its hover text and accessible name MUST give the state and the relative time of the last successful sync. This replaces 003 FR-006a's visible label.
- **FR-003**: The Strava connection card MUST show the last-sync line for each state in US2 scenario 2, with the matching dot, using the same last-sync time as 003 FR-006a.
- **FR-004**: Sign out MUST be an icon-only button with the hover text and accessible name "Sign out".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The top bar has no visible sync text or "Sign out" text, and every control in it has an accessible name.
- **SC-002**: The Settings card shows the same last-sync time the top bar's hover text does.

## Assumptions

- **The routes stay:** `/maintenance/due` and its page heading are unchanged. Only the link text changes.
- **Dot colours and the "not working" rule** (003 FR-006b) are unchanged.
- **Amends:** 003 (FR-006a and FR-006b presentation, and its UI contract), 002's header contract, 045 (the Mute card), 070 (the nav label next to its icon), and CLAUDE.md.
