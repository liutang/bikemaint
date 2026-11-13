# Feature Specification: Strava Sync Hardening (Retrospective)

**Feature Branch**: `017-spec-backfill` (retrospective; the work itself shipped on `011-strava-gear-scope`, `013-strava-pagination`, `014-reimport-strava-history` and `016-strava-timeout`)

**Created**: 2026-11-12

**Status**: Implemented (specified after the fact to restore spec-driven development)

**Input**: User description: "Retrospective spec for Strava sync hardening already shipped (PRs 011, 013, 014, 016): request profile access so the gear list is returned and show gear names with a reconnect hint when access is missing; fetch every page of Strava activities so backfill imports full history; re-import and unpair actions for Strava-paired bikes; allow slow Strava activity pages and report timeouts on re-import."

> This spec records behavior already merged to `master` (PRs #12, #14, #15, #17). It extends feature 001 (Strava pairing, backfill and sync) and does not change it. Acceptance scenarios below are taken from the existing tests, which remain the executable form of this spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pair a Bike With Its Strava Gear by Name (Priority: P1)

A rider opens "Pair with Strava" on a bike and sees their Strava bikes listed by name (for example "Madone SLR"), not by opaque gear codes. If Strava did not share the gear list because the rider approved only activity access, the screen explains what is wrong and offers a one-click way to reconnect and approve profile access.

**Why this priority**: Without a gear list the rider cannot pair a bike, so no Strava mileage reaches any bike. This was a hard blocker.

**Independent Test**: Sign in with a connection that has profile access and confirm gear appears by name; sign in with one that lacks it and confirm the reconnect explanation appears instead of a misleading "no gear" message.

**Acceptance Scenarios**:

1. **Given** Strava returns two bikes, **When** the rider opens the pairing screen, **Then** each is selectable by its Strava name.
2. **Given** Strava answered without a gear list, **When** the rider opens the pairing screen, **Then** the screen says Strava did not share the gear list, explains that signing in again and approving profile permission is needed, and offers a "Sign out and reconnect" button.
3. **Given** Strava returned an empty gear list, **When** the pairing screen opens, **Then** it says no unpaired gear was found and links to Strava's gear settings.
4. **Given** every Strava bike is already paired, **When** the pairing screen opens, **Then** the same "no unpaired gear" explanation is shown.
5. **Given** a stale or expired connection, **When** the pairing screen opens, **Then** the existing refresh message is kept and the profile-access message is not shown.
6. **Given** a new sign-in, **When** the rider is sent to Strava, **Then** both profile and activity read access are requested.

---

### User Story 2 - Backfill Imports the Full Ride History (Priority: P1)

When a bike is paired (or history is re-imported), every one of the rider's Strava activities is fetched, however many pages Strava splits them into, so mileage totals reflect the whole history and not just the first batch.

**Why this priority**: A history cut off after the first page gives silently wrong mileage and wrong maintenance projections.

**Independent Test**: Fake an activity feed of 401 activities in pages of 200 and confirm all 401 are imported.

**Acceptance Scenarios**:

1. **Given** Strava has 401 activities in pages of 200, **When** history is fetched, **Then** all 401 arrive and exactly three pages are requested.
2. **Given** Strava has no activities, **When** history is fetched, **Then** the result is empty after a single request.
3. **Given** an incremental sync with a "since" point, **When** history is fetched, **Then** only newer activities are requested, across as many pages as needed.

---

### User Story 3 - Re-import or Unpair a Strava-Paired Bike (Priority: P2)

On a paired bike's screen the rider sees "Re-import Strava history" and "Unpair from Strava". Re-import pulls the full history again without duplicating rides already imported. Unpair detaches the bike from its Strava gear but keeps every imported ride and its mileage. Unpaired bikes offer neither action.

**Why this priority**: Fixes a wrong or partial earlier import and allows pairing to a different Strava bike, without losing data. Not needed on first use.

**Independent Test**: Pair a bike, re-import twice and confirm the ride count is unchanged; unpair and confirm rides remain and "Pair with Strava" is offered again.

**Acceptance Scenarios**:

1. **Given** a paired bike, **When** its screen opens, **Then** both actions appear; an unpaired bike shows neither.
2. **Given** a paired bike, **When** the rider re-imports, **Then** the full backfill runs for that bike and the rider returns to the bike screen.
3. **Given** a bike already imported once, **When** history is re-imported again, **Then** no ride is duplicated.
4. **Given** a paired bike with imported rides, **When** the rider unpairs, **Then** the pairing is cleared, the rides stay, and "Pair with Strava" is offered again.
5. **Given** an unpaired bike, **When** re-import or unpair is requested directly, **Then** it is rejected as a conflict and nothing changes.
6. **Given** an unknown bike, **When** either action is requested, **Then** a not-found response is returned.

---

### User Story 4 - Slow Strava Responses Don't Break Re-import (Priority: P2)

Full-history pages can take much longer than ordinary requests. The app waits long enough for them, and if Strava still does not answer, the rider sees a plain message saying nothing was re-imported and to try again, instead of an error page.

**Why this priority**: Without it, large histories failed to import at all. Affects riders with long histories only.

**Independent Test**: Make the Strava call time out during re-import and confirm a clear retry message; confirm the activity request allows at least 30 seconds to respond.

**Acceptance Scenarios**:

1. **Given** Strava is slow to return an activity page, **When** history is fetched, **Then** the request waits at least 30 seconds before giving up.
2. **Given** Strava does not answer in time during re-import, **When** the rider re-imports, **Then** they see a message that Strava did not answer, nothing was re-imported, and to try again, and the app does not crash.

---

### Edge Cases

- A history that is an exact multiple of the page size ends with one empty page; fetching must terminate cleanly.
- A missing gear list differs from an empty one: missing means reconnect, empty means no Strava bikes (a null gear list is treated as missing).
- Re-import and unpair work only while signed in; all rides edited or deleted by the rider keep their protection from feature 006 (Strava upserts never overwrite them).
- Unpairing does not remove imported rides, so later re-pairing to the same gear updates rides in place rather than duplicating them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When signing in with Strava, the system MUST request both profile and activity read access.
- **FR-002**: The pairing screen MUST list Strava bikes by name, falling back to their identifier only if a name is absent.
- **FR-003**: The system MUST distinguish Strava omitting the gear list (profile access missing) from an empty list, and treat a null list as omitted.
- **FR-004**: When profile access is missing, the pairing screen MUST explain it and offer a one-click sign-out-and-reconnect action, and MUST NOT show the "no unpaired gear" message.
- **FR-005**: When there is no unpaired gear, the pairing screen MUST say so and link to Strava's gear settings.
- **FR-006**: Fetching activities MUST follow Strava's pages until a short or empty page is returned, and MUST return all activities, honoring an optional "since" point.
- **FR-007**: Requests for activity pages MUST allow at least 30 seconds for a response.
- **FR-008**: A paired bike MUST offer "Re-import Strava history" and "Unpair from Strava"; an unpaired bike MUST offer neither.
- **FR-009**: Re-import MUST run the full backfill for the bike, MUST NOT duplicate rides already imported, and MUST redirect to the bike screen.
- **FR-010**: Unpair MUST clear the bike's Strava gear pairing and pairing time, MUST keep all imported rides and mileage, and MUST redirect to the bike screen.
- **FR-011**: Re-import or unpair on an unpaired bike MUST be rejected as a conflict; on an unknown bike MUST return not found.
- **FR-012**: If Strava fails to answer during re-import, the system MUST respond with a gateway-failure status and a message that nothing was re-imported and the rider should try again.
- **FR-013**: Both actions MUST require sign-in, like every other route.
- **FR-014**: Unpairing, a missing gear list and a failed re-import MUST each leave a readable log line identifying the bike (never a token), so an operator can see what happened.

### Key Entities

- **Bike**: gains no new data; its existing Strava gear identifier and paired-at time are cleared by unpair and set by pairing.
- **Ride (Strava-sourced)**: identified by its Strava activity; re-import updates it in place, so history can be re-imported any number of times safely.
- **Strava connection**: the signed-in account's granted access, now including profile access.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider with profile access sees their Strava bikes by name and can pair one in a single step.
- **SC-002**: A rider without profile access can reach a working pairing screen in two clicks (reconnect, then approve) following only on-screen guidance.
- **SC-003**: A history of 400+ activities imports completely, with 100% of activities counted in mileage.
- **SC-004**: Re-importing the same history any number of times leaves the ride count unchanged.
- **SC-005**: Unpairing leaves 100% of previously imported rides and mileage intact.
- **SC-006**: A Strava outage or slow response during re-import ends in a plain retry message, never an error page.

## Assumptions

- The rider is the single account holder (feature 001); no multi-user concerns apply.
- Strava's gear list is returned only with profile access, and activity pages are at most 200 per request.
- Re-import is manual; scheduled sync (feature 001) is unchanged.
- Re-pairing after unpair is the existing pairing flow; no extra confirmation step is added.
